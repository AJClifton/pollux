import json
from unittest.mock import patch

from app.services import geocoding_service


SAMPLE_GEOCODE_RESPONSE = {
    "results": [
        {
            "name": "London",
            "latitude": 51.5085,
            "longitude": -0.1257,
            "country": "United Kingdom",
            "admin1": "England",
        }
    ]
}


class TestGetCoordinates:

    def test_get_coordinates_cachedInRedis_returnsCachedData(self, app, mock_redis):
        # Arrange
        cached = [{"name": "London", "latitude": 51.51, "longitude": -0.13,
                    "country": "United Kingdom", "admin1": "England"}]
        mock_redis.get.return_value = json.dumps(cached)

        with app.app_context():
            # Act
            result = geocoding_service.get_coordinates("London")

            # Assert
            assert result == cached

    def test_get_coordinates_redisMiss_fetchesFromApi(self, app, mock_redis):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_geocode",
                return_value=SAMPLE_GEOCODE_RESPONSE,
            ):
                # Act
                result = geocoding_service.get_coordinates("London")

                # Assert
                assert len(result) == 1
                assert result[0]["name"] == "London"
                assert result[0]["latitude"] == 51.5085

    def test_get_coordinates_normalizesName_sameKey(self, app, mock_redis):
        # Arrange
        cached = [{"name": "London", "latitude": 51.51, "longitude": -0.13,
                    "country": "UK", "admin1": "England"}]
        mock_redis.get.return_value = json.dumps(cached)

        with app.app_context():
            # Act
            geocoding_service.get_coordinates("  London  ")

            # Assert
            mock_redis.get.assert_called_with("geocode:london")

    def test_get_coordinates_apiReturnsEmpty_returnsEmptyList(self, app, mock_redis):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_geocode",
                return_value={"results": []},
            ):
                # Act
                result = geocoding_service.get_coordinates("xyznonexistent")

                # Assert
                assert result == []

    def test_get_coordinates_cachesResult_setsRedis(self, app, mock_redis):
        # Arrange
        with app.app_context():
            with patch(
                "app.services.open_meteo_client.OpenMeteoClient.fetch_geocode",
                return_value=SAMPLE_GEOCODE_RESPONSE,
            ):
                # Act
                geocoding_service.get_coordinates("London")

                # Assert
                mock_redis.setex.assert_called_once()
                call_args = mock_redis.setex.call_args
                assert call_args[0][0] == "geocode:london"
