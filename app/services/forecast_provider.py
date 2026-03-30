import logging
from datetime import datetime, timedelta

from app.core.extensions import db, utcnow
from app.models.daily_forecast import DailyForecastModel
from app.models.hourly_forecast import HourlyForecastModel
from app.services.request_coalescer import forecast_coalescer

logger = logging.getLogger(__name__)


def _night_window(sunset_str, sunrise_str):
    """Return (start, end) datetimes covering 1+ hour before sunset to 1+ hour after next-day sunrise."""
    sunset_dt = datetime.fromisoformat(sunset_str)
    sunrise_dt = datetime.fromisoformat(sunrise_str)
    start = sunset_dt.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    sunrise_floor = sunrise_dt.replace(minute=0, second=0, microsecond=0)
    end = sunrise_floor + timedelta(hours=1 if sunrise_dt == sunrise_floor else 2)
    return start, end


class ForecastProvider:

    def __init__(self, client):
        self._client = client

    def get_from_db(self, lat, lon, ttl, model_cls):
        """Query DB for rows fetched within TTL. Returns list of dicts or None if no fresh data."""
        cutoff = utcnow() - timedelta(seconds=ttl)
        sort_col = model_cls.datetime if hasattr(model_cls, "datetime") else model_cls.date
        rows = model_cls.query.filter(
            model_cls.latitude == lat,
            model_cls.longitude == lon,
            model_cls.fetched_at >= cutoff,
        ).order_by(sort_col.asc()).all()
        return [row.to_dict() for row in rows] if rows else None

    def get_night_forecast_from_db(self, lat, lon, date, ttl):
        """Query DB for hourly rows within the night window for date -> date+1."""
        cutoff = utcnow() - timedelta(seconds=ttl)
        next_date = date + timedelta(days=1)

        daily_rows = DailyForecastModel.query.filter(
            DailyForecastModel.latitude == lat,
            DailyForecastModel.longitude == lon,
            DailyForecastModel.date.in_([date, next_date]),
            DailyForecastModel.fetched_at >= cutoff,
        ).all()

        if len(daily_rows) < 2:
            return None

        by_date = {row.date: row for row in daily_rows}
        today = by_date.get(date)
        tomorrow = by_date.get(next_date)

        if not today or not today.sunset or not tomorrow or not tomorrow.sunrise:
            return None

        start, end = _night_window(today.sunset, tomorrow.sunrise)

        hourly_rows = HourlyForecastModel.query.filter(
            HourlyForecastModel.latitude == lat,
            HourlyForecastModel.longitude == lon,
            HourlyForecastModel.fetched_at >= cutoff,
            HourlyForecastModel.datetime >= start,
            HourlyForecastModel.datetime <= end,
        ).order_by(HourlyForecastModel.datetime.asc()).all()

        if not hourly_rows:
            return None

        return {"latitude": lat, "longitude": lon, "hourly": [row.to_dict() for row in hourly_rows]}

    def get_hourly(self, lat, lon, date, db_ttl):
        """DB → API fallback for hourly (night window) forecast. Returns hourly result dict."""
        result = self.get_night_forecast_from_db(lat, lon, date, db_ttl)
        if result is not None:
            return result
        hourly_result, daily_result = self.fetch_from_api(lat, lon)
        return self._apply_night_window(hourly_result, daily_result, date)

    def get_daily(self, lat, lon, db_ttl):
        """DB → API fallback for daily forecast. Returns daily result dict."""
        rows = self.get_from_db(lat, lon, db_ttl, DailyForecastModel)
        if rows is not None:
            return {"latitude": lat, "longitude": lon, "daily": rows}
        _, daily_result = self.fetch_from_api(lat, lon)
        return daily_result

    def _apply_night_window(self, hourly_result, daily_result, date):
        """Filter hourly result to the night window defined by sunset/sunrise in daily_result."""
        date_str = date.isoformat()
        next_date_str = (date + timedelta(days=1)).isoformat()
        sunset = sunrise = None
        for d in daily_result.get("daily", []):
            if d.get("date") == date_str and (v := d.get("sunset")):
                sunset = v
            elif d.get("date") == next_date_str and (v := d.get("sunrise")):
                sunrise = v
            if sunset and sunrise:
                break
        if sunset is None or sunrise is None:
            logger.warning(
                "Could not find sunset/sunrise for %s: returning unfiltered hourly data.", date_str
            )
            return hourly_result
        start, end = _night_window(sunset, sunrise)
        filtered = [
            h for h in hourly_result.get("hourly", [])
            if start <= datetime.fromisoformat(h["datetime"]) <= end
        ]
        return {
            "latitude": hourly_result["latitude"],
            "longitude": hourly_result["longitude"],
            "hourly": filtered,
        }

    def fetch_from_api(self, lat, lon):
        """Fetch from Open-Meteo, parse, store to DB, and return (hourly_result, daily_result)."""
        api_data = forecast_coalescer.execute(
            f"forecast:{lat}:{lon}", self._client.fetch_forecast, lat, lon
        )
        hourly_rows, daily_rows = self._client.parse_forecast(lat, lon, api_data)
        self._store_forecast(lat, lon, hourly_rows, daily_rows)
        hourly_result = {
            "latitude": lat, "longitude": lon,
            "hourly": [self._serialize_row(r, "datetime") for r in hourly_rows],
        }
        daily_result = {
            "latitude": lat, "longitude": lon,
            "daily": [self._serialize_row(r, "date") for r in daily_rows],
        }
        return hourly_result, daily_result

    def _store_forecast(self, lat, lon, hourly_rows, daily_rows):
        """Persist parsed forecast rows to DB."""
        self._upsert_rows(lat, lon, hourly_rows, HourlyForecastModel, "datetime")
        self._upsert_rows(lat, lon, daily_rows, DailyForecastModel, "date")
        db.session.commit()

    def _upsert_rows(self, lat, lon, rows, model_cls, time_key):
        """Bulk insert/update rows into the DB. Does not commit."""
        if not rows:
            return

        parsed_times = [r[time_key] for r in rows]
        time_col = getattr(model_cls, time_key)
        existing_times = {
            t for (t,) in db.session.query(time_col).filter(
                model_cls.latitude == lat,
                model_cls.longitude == lon,
                time_col.in_(parsed_times),
            ).all()
        }

        inserts, updates = [], []
        for d in rows:
            (updates if d[time_key] in existing_times else inserts).append(d)

        if inserts:
            db.session.bulk_insert_mappings(model_cls, inserts)
        if updates:
            db.session.bulk_update_mappings(model_cls, updates)

    def _serialize_row(self, row_data, time_key):
        """Convert a row dict to API-serializable form: isoformat the time field, drop fetched_at."""
        d = {k: v for k, v in row_data.items() if k != "fetched_at"}
        d[time_key] = d[time_key].isoformat()
        return d
