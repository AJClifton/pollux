from app.core.extensions import db, utcnow


class HourlyForecastModel(db.Model):
    __tablename__ = "hourly_forecasts"

    latitude = db.Column(db.Float, primary_key=True)
    longitude = db.Column(db.Float, primary_key=True)
    datetime = db.Column(db.DateTime, primary_key=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    temperature = db.Column(db.Float)
    dewpoint = db.Column(db.Float)
    rain = db.Column(db.Float)
    cloud_cover_total = db.Column(db.Float)
    cloud_cover_low = db.Column(db.Float)
    cloud_cover_mid = db.Column(db.Float)
    cloud_cover_high = db.Column(db.Float)
    visibility = db.Column(db.Float)
    surface_pressure = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.Float)
    wind_gusts = db.Column(db.Float)

    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "datetime": self.datetime.isoformat(),
            "temperature": self.temperature,
            "dewpoint": self.dewpoint,
            "rain": self.rain,
            "cloud_cover_total": self.cloud_cover_total,
            "cloud_cover_low": self.cloud_cover_low,
            "cloud_cover_mid": self.cloud_cover_mid,
            "cloud_cover_high": self.cloud_cover_high,
            "visibility": self.visibility,
            "surface_pressure": self.surface_pressure,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "wind_gusts": self.wind_gusts,
        }
