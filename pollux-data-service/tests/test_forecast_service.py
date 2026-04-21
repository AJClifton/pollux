import json
from datetime import datetime, timedelta, date
from unittest.mock import patch

from app.core.extensions import utcnow
from app.models.hourly_forecast import HourlyForecastModel
from app.models.daily_forecast import DailyForecastModel
from app.services.hourly_forecast import HourlyForecast
from app.services.daily_forecast import DailyForecast


# Hourly times fall within the night window for date 2026-03-24:
# sunset "2026-03-24T19:30" → window start 18:00; sunrise "2026-03-25T06:13" → window end 08:00
SAMPLE_API_RESPONSE = {
    "hourly": {
        "time": ["2026-03-24T21:00", "2026-03-24T22:00"],
        "temperature_2m": [10.5, 9.8],
        "dewpoint_2m": [5.0, 4.5],
        "rain": [0.0, 0.1],
        "cloud_cover": [50.0, 60.0],
        "cloud_cover_low": [20.0, 30.0],
        "cloud_cover_mid": [15.0, 20.0],
        "cloud_cover_high": [10.0, 10.0],
        "visibility": [10000.0, 8000.0],
        "surface_pressure": [1013.0, 1012.5],
        "wind_speed_10m": [5.0, 6.0],
        "wind_direction_10m": [180.0, 190.0],
        "wind_gusts_10m": [10.0, 12.0],
    },
    "daily": {
        "time": ["2026-03-24", "2026-03-25"],
        "weather_code": [3, 2],
        "temperature_2m_max": [12.0, 11.0],
        "temperature_2m_min": [8.0, 7.0],
        "precipitation_sum": [0.1, 0.0],
        "precipitation_probability_max": [20.0, 10.0],
        "wind_speed_10m_max": [15.0, 12.0],
        "sunset": ["2026-03-24T19:30", "2026-03-25T19:32"],
        "sunrise": ["2026-03-24T06:15", "2026-03-25T06:13"],
    },
}

TARGET_DATE = date(2026, 3, 24)


class TestGetHourlyForecast:

    def test_get_hourly_forecast_cachedInRedis_returnsCachedData(self, app, mock_redis):
        # Arrange
        cached = {"latitude": 51.51, "longitude": -0.13, "hourly": [
            {"datetime": "2026-03-24T21:00", "temperature": 10.5},
        ]}
        mock_redis.get.return_value = json.dumps(cached)

        with app.app_context():
            # Act
            result = HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

            # Assert
            assert result["latitude"] == 51.51
            assert len(result["hourly"]) == 1
            mock_redis.get.assert_called_once_with("forecast:hourly:51.51:-0.13:2026-03-24")

    def test_get_hourly_forecast_redisMissDbHit_returnsDbData(self, app, mock_redis, db_session):
        # Arrange - night of 2026-03-23 to 2026-03-24; midnight falls within the window
        hourly_row = HourlyForecastModel(
            latitude=51.51, longitude=-0.13,
            datetime=datetime(2026, 3, 24, 0, 0),
            fetched_at=utcnow(),
            temperature=10.5, dewpoint=5.0, rain=0.0,
            cloud_cover_total=50.0, cloud_cover_low=20.0,
            cloud_cover_mid=15.0, cloud_cover_high=10.0,
            visibility=10000.0, surface_pressure=1013.0,
            wind_speed=5.0, wind_direction=180.0, wind_gusts=10.0,
        )
        daily_row_23 = DailyForecastModel(
            latitude=51.51, longitude=-0.13,
            date=date(2026, 3, 23),
            fetched_at=utcnow(),
            weather_code=3, maximum_temperature=12.0, minimum_temperature=8.0,
            precipitation_sum=0.1, precipitation_probability_max=20.0,
            maximum_wind_speed=15.0,
            sunset="2026-03-23T19:30",
        )
        daily_row_24 = DailyForecastModel(
            latitude=51.51, longitude=-0.13,
            date=date(2026, 3, 24),
            fetched_at=utcnow(),
            weather_code=2, maximum_temperature=11.0, minimum_temperature=7.0,
            precipitation_sum=0.0, precipitation_probability_max=10.0,
            maximum_wind_speed=12.0,
            sunrise="2026-03-24T06:15",
        )
        db_session.add_all([hourly_row, daily_row_23, daily_row_24])
        db_session.commit()

        with app.app_context():
            # Act
            result = HourlyForecast(51.51, -0.13, date(2026, 3, 23)).to_dict()

            # Assert
            assert result["latitude"] == 51.51
            assert len(result["hourly"]) == 1
            assert result["hourly"][0]["temperature"] == 10.5

    def test_get_hourly_forecast_staleDbData_fetchesFromApi(self, app, mock_redis, db_session):
        # Arrange
        row = HourlyForecastModel(
            latitude=51.51, longitude=-0.13,
            datetime=datetime(2026, 3, 24, 0, 0),
            fetched_at=utcnow() - timedelta(hours=2),
            temperature=10.5, dewpoint=5.0, rain=0.0,
            cloud_cover_total=50.0, cloud_cover_low=20.0,
            cloud_cover_mid=15.0, cloud_cover_high=10.0,
            visibility=10000.0, surface_pressure=1013.0,
            wind_speed=5.0, wind_direction=180.0, wind_gusts=10.0,
        )
        db_session.add(row)
        db_session.commit()

        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=SAMPLE_API_RESPONSE,
            ) as mock_fetch:
                # Act
                HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

                # Assert
                mock_fetch.assert_called_once()

    def test_get_hourly_forecast_allMiss_returnsFilteredHourly(self, app, mock_redis):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=SAMPLE_API_RESPONSE,
            ):
                # Act
                result = HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

                # Assert
                assert result["latitude"] == 51.51
                assert len(result["hourly"]) == 2
                assert "daily" not in result
                assert result["hourly"][0]["temperature"] == 10.5

    def test_get_hourly_forecast_apiResponse_persistsBothToDb(self, app, mock_redis, db_session):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=SAMPLE_API_RESPONSE,
            ):
                # Act
                HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

                # Assert
                hourly_count = HourlyForecastModel.query.filter_by(
                    latitude=51.51, longitude=-0.13
                ).count()
                daily_count = DailyForecastModel.query.filter_by(
                    latitude=51.51, longitude=-0.13
                ).count()
                assert hourly_count == 2
                assert daily_count == 2

    def test_get_hourly_forecast_roundsCoordinates_usesSameKey(self, app, mock_redis):
        # Arrange
        cached = {"latitude": 51.51, "longitude": -0.13, "hourly": [
            {"datetime": "2026-03-24T21:00", "temperature": 10.5},
        ]}
        mock_redis.get.return_value = json.dumps(cached)

        with app.app_context():
            # Act
            result = HourlyForecast(51.5074, -0.1278, TARGET_DATE).to_dict()

            # Assert
            assert result["latitude"] == 51.51
            assert mock_redis.get.call_args_list[0][0][0] == (
                "forecast:hourly:51.51:-0.13:2026-03-24"
            )

    def test_get_hourly_forecast_hoursOutsideWindow_areExcluded(self, app, mock_redis):
        # Arrange - sunset 19:30 → window start 18:00; sunrise 06:13 → window end 08:00
        api_response = {
            **SAMPLE_API_RESPONSE,
            "hourly": {
                **SAMPLE_API_RESPONSE["hourly"],
                "time": [
                    "2026-03-24T17:00",  # before window
                    "2026-03-24T21:00",  # in window
                    "2026-03-25T09:00",  # after window
                ],
                "temperature_2m": [8.0, 10.5, 12.0],
                "dewpoint_2m": [4.0, 5.0, 6.0],
                "rain": [0.0, 0.0, 0.0],
                "cloud_cover": [20.0, 50.0, 30.0],
                "cloud_cover_low": [10.0, 20.0, 15.0],
                "cloud_cover_mid": [5.0, 15.0, 10.0],
                "cloud_cover_high": [5.0, 10.0, 5.0],
                "visibility": [15000.0, 10000.0, 12000.0],
                "surface_pressure": [1015.0, 1013.0, 1014.0],
                "wind_speed_10m": [3.0, 5.0, 4.0],
                "wind_direction_10m": [170.0, 180.0, 175.0],
                "wind_gusts_10m": [6.0, 10.0, 8.0],
            },
        }

        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=api_response,
            ):
                # Act
                result = HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

                # Assert
                assert len(result["hourly"]) == 1
                assert result["hourly"][0]["datetime"] == "2026-03-24T21:00:00"

    def test_get_hourly_forecast_windowBoundaries_areInclusive(self, app, mock_redis):
        # Arrange - sunset 19:30 → start 18:00; sunrise 06:00 (exact hour) → end 07:00
        api_response = {
            **SAMPLE_API_RESPONSE,
            "daily": {
                **SAMPLE_API_RESPONSE["daily"],
                "sunrise": ["2026-03-24T06:15", "2026-03-25T06:00"],  # exact hour sunrise
            },
            "hourly": {
                **SAMPLE_API_RESPONSE["hourly"],
                "time": ["2026-03-24T18:00", "2026-03-25T07:00"],  # boundary hours
                "temperature_2m": [10.5, 9.8],
            },
        }

        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=api_response,
            ):
                # Act
                result = HourlyForecast(51.51, -0.13, TARGET_DATE).to_dict()

                # Assert - both boundary hours included
                assert len(result["hourly"]) == 2


class TestGetDailyForecast:

    def test_get_daily_forecast_cachedInRedis_returnsCachedData(self, app, mock_redis):
        # Arrange
        cached_data = {"latitude": 51.51, "longitude": -0.13, "daily": []}
        mock_redis.get.return_value = json.dumps(cached_data)

        with app.app_context():
            # Act
            result = DailyForecast(51.51, -0.13).to_dict()

            # Assert
            assert result == cached_data
            mock_redis.get.assert_called_with("forecast:daily:51.51:-0.13")

    def test_get_daily_forecast_redisMissDbHit_returnsDbData(self, app, mock_redis, db_session):
        # Arrange
        row = DailyForecastModel(
            latitude=51.51, longitude=-0.13,
            date=datetime(2026, 3, 24).date(),
            fetched_at=utcnow(),
            weather_code=3, maximum_temperature=12.0, minimum_temperature=8.0,
            precipitation_sum=0.1, precipitation_probability_max=20.0,
            maximum_wind_speed=15.0,
        )
        db_session.add(row)
        db_session.commit()

        with app.app_context():
            # Act
            result = DailyForecast(51.51, -0.13).to_dict()

            # Assert
            assert result["latitude"] == 51.51
            assert len(result["daily"]) == 1
            assert result["daily"][0]["weather_code"] == 3

    def test_get_daily_forecast_allMiss_returnsDailyOnly(self, app, mock_redis):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_forecast",
                return_value=SAMPLE_API_RESPONSE,
            ):
                # Act
                result = DailyForecast(51.51, -0.13).to_dict()

                # Assert
                assert result["latitude"] == 51.51
                assert len(result["daily"]) == 2
                assert "hourly" not in result
                assert result["daily"][0]["weather_code"] == 3
