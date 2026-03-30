from unittest.mock import patch, MagicMock

import requests

from app.services.open_meteo_client import OpenMeteoClient


class TestFetchForecast:

    def test_fetch_forecast_validCoords_returnsJson(self, app):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"hourly": {}, "daily": {}}
        mock_response.raise_for_status = MagicMock()
        client = OpenMeteoClient()

        with app.app_context():
            with patch.object(requests, "get", return_value=mock_response) as mock_get:
                # Act
                result = client.fetch_forecast(51.51, -0.13)

                # Assert
                assert result == {"hourly": {}, "daily": {}}
                mock_get.assert_called_once()
                args, kwargs = mock_get.call_args
                assert kwargs["params"]["latitude"] == 51.51
                assert kwargs["params"]["longitude"] == -0.13

    def test_fetch_forecast_httpError_raises(self, app):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        client = OpenMeteoClient()

        with app.app_context():
            with patch.object(requests, "get", return_value=mock_response):
                # Act & Assert
                try:
                    client.fetch_forecast(51.51, -0.13)
                    assert False, "Should have raised"
                except requests.HTTPError:
                    pass

    def test_fetch_forecast_timeout_raises(self, app):
        # Arrange
        client = OpenMeteoClient()

        with app.app_context():
            with patch.object(
                requests, "get", side_effect=requests.Timeout("timed out")
            ):
                # Act & Assert
                try:
                    client.fetch_forecast(51.51, -0.13)
                    assert False, "Should have raised"
                except requests.Timeout:
                    pass


class TestFetchGeocode:

    def test_fetch_geocode_validName_returnsJson(self, app):
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"name": "London", "latitude": 51.51, "longitude": -0.13}]
        }
        mock_response.raise_for_status = MagicMock()
        client = OpenMeteoClient()

        with app.app_context():
            with patch.object(requests, "get", return_value=mock_response) as mock_get:
                # Act
                result = client.fetch_geocode("London")

                # Assert
                assert result["results"][0]["name"] == "London"
                args, kwargs = mock_get.call_args
                assert kwargs["params"]["name"] == "London"

    def test_fetch_geocode_httpError_raises(self, app):
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        client = OpenMeteoClient()

        with app.app_context():
            with patch.object(requests, "get", return_value=mock_response):
                # Act & Assert
                try:
                    client.fetch_geocode("London")
                    assert False, "Should have raised"
                except requests.HTTPError:
                    pass
