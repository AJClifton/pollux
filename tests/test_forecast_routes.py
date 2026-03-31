from unittest.mock import patch, MagicMock


SAMPLE_HOURLY = {
    "latitude": 51.51,
    "longitude": -0.13,
    "hourly": [{"temperature": 10.5}],
}

SAMPLE_DAILY = {
    "latitude": 51.51,
    "longitude": -0.13,
    "daily": [{"weather_code": 3}],
}

SAMPLE_GEOCODE = [
    {"name": "London", "latitude": 51.51, "longitude": -0.13,
     "country": "United Kingdom", "admin1": "England"}
]


def _mock_hourly_class(return_value=SAMPLE_HOURLY, side_effect=None):
    """Create a mock that replaces the HourlyForecast class."""
    mock_cls = MagicMock()
    if side_effect:
        mock_cls.side_effect = side_effect
    else:
        mock_cls.return_value.to_dict.return_value = return_value
    return mock_cls


def _mock_daily_class(return_value=SAMPLE_DAILY, side_effect=None):
    """Create a mock that replaces the DailyForecast class."""
    mock_cls = MagicMock()
    if side_effect:
        mock_cls.side_effect = side_effect
    else:
        mock_cls.return_value.to_dict.return_value = return_value
    return mock_cls


class TestHourlyForecastRoute:

    def test_get_hourly_forecast_validLatLon_returns200(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.HourlyForecast",
            _mock_hourly_class(),
        ):
            # Act
            response = client.get("/api/forecast/hourly?lat=51.51&lon=-0.13&date=2026-03-24")

            # Assert
            assert response.status_code == 200
            data = response.get_json()
            assert data["latitude"] == 51.51
            assert "hourly" in data

    def test_get_hourly_forecast_validLocation_returns200(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.geocoding_service.get_coordinates",
            return_value=SAMPLE_GEOCODE,
        ), patch(
            "app.api.forecast.HourlyForecast",
            _mock_hourly_class(),
        ):
            # Act
            response = client.get("/api/forecast/hourly?location=London&date=2026-03-24")

            # Assert
            assert response.status_code == 200
            data = response.get_json()
            assert data["latitude"] == 51.51

    def test_get_hourly_forecast_noParams_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/forecast/hourly")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_hourly_forecast_missingDate_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/forecast/hourly?lat=51.51&lon=-0.13")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_hourly_forecast_invalidDate_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/forecast/hourly?lat=51.51&lon=-0.13&date=not-a-date")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_hourly_forecast_locationNotFound_returns404(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.geocoding_service.get_coordinates",
            return_value=[],
        ):
            # Act
            response = client.get("/api/forecast/hourly?location=xyznonexistent&date=2026-03-24")

            # Assert
            assert response.status_code == 404

    def test_get_hourly_forecast_dateTooFarInFuture_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/forecast/hourly?lat=51.51&lon=-0.13&date=2099-01-01")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_hourly_forecast_upstreamFailure_returns502(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.HourlyForecast",
            _mock_hourly_class(side_effect=Exception("API down")),
        ):
            # Act
            response = client.get("/api/forecast/hourly?lat=51.51&lon=-0.13&date=2026-03-24")

            # Assert
            assert response.status_code == 502


class TestDailyForecastRoute:

    def test_get_daily_forecast_validLatLon_returns200(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.DailyForecast",
            _mock_daily_class(),
        ):
            # Act
            response = client.get("/api/forecast/daily?lat=51.51&lon=-0.13")

            # Assert
            assert response.status_code == 200
            data = response.get_json()
            assert data["latitude"] == 51.51
            assert "daily" in data

    def test_get_daily_forecast_noParams_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/forecast/daily")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_daily_forecast_upstreamFailure_returns502(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.forecast.DailyForecast",
            _mock_daily_class(side_effect=Exception("API down")),
        ):
            # Act
            response = client.get("/api/forecast/daily?lat=51.51&lon=-0.13")

            # Assert
            assert response.status_code == 502
