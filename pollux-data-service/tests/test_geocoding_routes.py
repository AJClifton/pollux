from unittest.mock import patch


SAMPLE_RESULTS = [
    {"name": "London", "latitude": 51.51, "longitude": -0.13,
     "country": "United Kingdom", "admin1": "England"}
]


class TestGeocodingRoute:

    def test_get_geocode_validName_returns200(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.geocoding.geocoding_service.get_coordinates",
            return_value=SAMPLE_RESULTS,
        ):
            # Act
            response = client.get("/api/geocode?name=London")

            # Assert
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["results"]) == 1
            assert data["results"][0]["name"] == "London"

    def test_get_geocode_missingName_returns400(self, client, mock_redis):
        # Arrange / Act
        response = client.get("/api/geocode")

        # Assert
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_get_geocode_upstreamFailure_returns502(self, client, mock_redis):
        # Arrange
        with patch(
            "app.api.geocoding.geocoding_service.get_coordinates",
            side_effect=Exception("API down"),
        ):
            # Act
            response = client.get("/api/geocode?name=London")

            # Assert
            assert response.status_code == 502
