"""
Time Tracking Service for monitoring user session hours.

Tracks cumulative time spent by each user and generates reports
when the target hours (default 35) are reached.
"""

import json
import atexit
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

from ..core import get_logger, Logger


@dataclass
class SessionRecord:
    """Record of a single session."""

    start_time: str
    end_time: str
    duration_seconds: float
    workflow: str

    @property
    def duration(self) -> timedelta:
        """Get duration as timedelta."""
        return timedelta(seconds=self.duration_seconds)

    @property
    def duration_formatted(self) -> str:
        """Get duration as HH:MM:SS string."""
        total_seconds = int(self.duration_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@dataclass
class UserTimeData:
    """Time tracking data for a user."""

    email: str
    total_seconds: float
    target_hours: float
    sessions: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    completed: bool = False
    completed_at: Optional[str] = None

    @property
    def total_hours(self) -> float:
        """Get total hours as float."""
        return self.total_seconds / 3600

    @property
    def remaining_hours(self) -> float:
        """Get remaining hours to reach target."""
        return max(0, self.target_hours - self.total_hours)

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        return min(100, (self.total_hours / self.target_hours) * 100)

    @property
    def total_formatted(self) -> str:
        """Get total time as HH:MM:SS string."""
        total_seconds = int(self.total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class TimeTracker:
    """
    Service for tracking user session time.

    Persists data to a JSON file and generates reports
    when target hours are reached.

    Attributes:
        user_email: Email identifying the user
        target_hours: Target hours to complete (default 35)
        data_dir: Directory for data files
    """

    DEFAULT_TARGET_HOURS = 35.0
    DATA_FILE_NAME = "time_tracking.json"
    REPORTS_DIR_NAME = "reports"

    def __init__(
        self,
        user_email: str,
        target_hours: float = DEFAULT_TARGET_HOURS,
        data_dir: str = "data",
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the time tracker.

        Args:
            user_email: User email for identification
            target_hours: Target hours to complete
            data_dir: Directory for storing data files
            logger: Optional logger instance
        """
        self._user_email = self._sanitize_email(user_email)
        self._target_hours = target_hours
        self._data_dir = Path(data_dir)
        self._logger = logger or get_logger("TimeTracker")

        self._session_start: Optional[datetime] = None
        self._current_workflow: str = "unknown"

        # Ensure directories exist
        self._data_dir.mkdir(parents=True, exist_ok=True)
        (self._data_dir / self.REPORTS_DIR_NAME).mkdir(exist_ok=True)

        # Load existing data
        self._data = self._load_or_create_user_data()

        # Register cleanup on exit
        atexit.register(self._cleanup_on_exit)

    @property
    def data_file_path(self) -> Path:
        """Get path to the data file."""
        return self._data_dir / self.DATA_FILE_NAME

    @property
    def total_hours(self) -> float:
        """Get total hours tracked."""
        return self._data.total_hours

    @property
    def remaining_hours(self) -> float:
        """Get remaining hours."""
        return self._data.remaining_hours

    @property
    def progress_percent(self) -> float:
        """Get progress percentage."""
        return self._data.progress_percent

    @property
    def is_complete(self) -> bool:
        """Check if target hours are complete."""
        return self._data.completed or self._data.total_hours >= self._target_hours

    @property
    def session_count(self) -> int:
        """Get total number of sessions."""
        return len(self._data.sessions)

    # ==================== Session Management ====================

    def start_session(self, workflow: str = "unknown") -> None:
        """
        Start a new tracking session.

        Args:
            workflow: Name of the workflow being run
        """
        self._session_start = datetime.now()
        self._current_workflow = workflow

        self._logger.info(f"Session started for {self._user_email}")
        self._logger.info(
            f"Current progress: {self._data.total_formatted} / "
            f"{self._target_hours:.1f}h ({self.progress_percent:.1f}%)"
        )

        if self.is_complete:
            self._logger.info("🎉 Target hours already completed!")

    def end_session(self) -> SessionRecord:
        """
        End the current session and save data.

        Returns:
            SessionRecord with session details
        """
        if not self._session_start:
            raise RuntimeError("No active session to end")

        end_time = datetime.now()
        duration = end_time - self._session_start

        # Create session record
        record = SessionRecord(
            start_time=self._session_start.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration.total_seconds(),
            workflow=self._current_workflow,
        )

        # Update data
        self._data.total_seconds += duration.total_seconds()
        self._data.sessions.append(asdict(record))
        self._data.updated_at = datetime.now().isoformat()

        # Check completion
        was_complete = self._data.completed
        if not was_complete and self._data.total_hours >= self._target_hours:
            self._data.completed = True
            self._data.completed_at = datetime.now().isoformat()
            self._on_completion()

        # Save and log
        self._save_data()
        self._log_session_summary(record)

        self._session_start = None

        return record

    def _on_completion(self) -> None:
        """Handle completion of target hours."""
        self._logger.info("=" * 50)
        self._logger.info("🎉 ¡FELICIDADES! 35 HORAS COMPLETADAS 🎉")
        self._logger.info("=" * 50)

        # Generate completion report
        report_path = self.generate_report()
        self._logger.info(f"Reporte generado: {report_path}")

    def _log_session_summary(self, record: SessionRecord) -> None:
        """Log session summary."""
        self._logger.info(f"Session ended: {record.duration_formatted}")
        self._logger.info(
            f"Total acumulado: {self._data.total_formatted} / "
            f"{self._target_hours:.1f}h ({self.progress_percent:.1f}%)"
        )
        self._logger.info(f"Horas restantes: {self.remaining_hours:.2f}h")

    # ==================== Data Persistence ====================

    def _load_or_create_user_data(self) -> UserTimeData:
        """Load existing user data or create new."""
        all_data = self._load_all_data()

        if self._user_email in all_data:
            user_dict = all_data[self._user_email]
            return UserTimeData(**user_dict)

        # Create new user data
        now = datetime.now().isoformat()
        return UserTimeData(
            email=self._user_email,
            total_seconds=0.0,
            target_hours=self._target_hours,
            sessions=[],
            created_at=now,
            updated_at=now,
        )

    def _load_all_data(self) -> Dict[str, Any]:
        """Load all user data from file."""
        if not self.data_file_path.exists():
            return {}

        try:
            with open(self.data_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._logger.warn(f"Error loading data: {e}")
            return {}

    def _save_data(self) -> None:
        """Save current user data to file."""
        all_data = self._load_all_data()
        all_data[self._user_email] = asdict(self._data)

        try:
            with open(self.data_file_path, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self._logger.error(f"Error saving data: {e}")

    # ==================== Reports ====================

    def generate_report(self) -> Path:
        """
        Generate a detailed report for the user.

        Returns:
            Path to the generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_email = self._user_email.replace("@", "_at_").replace(".", "_")
        report_name = f"reporte_{safe_email}_{timestamp}.txt"
        report_path = self._data_dir / self.REPORTS_DIR_NAME / report_name

        lines = [
            "=" * 60,
            "REPORTE DE HORAS - ROSETTA STONE BOT",
            "=" * 60,
            "",
            f"Usuario: {self._data.email}",
            f"Fecha del reporte: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "-" * 40,
            "RESUMEN",
            "-" * 40,
            f"Horas objetivo: {self._target_hours:.1f}h",
            f"Horas completadas: {self._data.total_hours:.2f}h ({self._data.total_formatted})",
            f"Progreso: {self.progress_percent:.1f}%",
            f"Horas restantes: {self.remaining_hours:.2f}h",
            f"Estado: {'✅ COMPLETADO' if self.is_complete else '⏳ EN PROGRESO'}",
            "",
            f"Total de sesiones: {len(self._data.sessions)}",
            f"Primera sesión: {self._data.created_at[:10] if self._data.sessions else 'N/A'}",
            f"Última actualización: {self._data.updated_at[:10]}",
        ]

        if self._data.completed_at:
            lines.append(f"Fecha de completado: {self._data.completed_at[:10]}")

        lines.extend(
            [
                "",
                "-" * 40,
                "HISTORIAL DE SESIONES",
                "-" * 40,
            ]
        )

        for i, session in enumerate(self._data.sessions, 1):
            start = session["start_time"][:19].replace("T", " ")
            duration_secs = session["duration_seconds"]
            hours, remainder = divmod(int(duration_secs), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            workflow = session.get("workflow", "unknown")
            lines.append(f"  {i:3d}. {start} | {duration_str} | {workflow}")

        lines.extend(
            [
                "",
                "=" * 60,
                "Generado automáticamente por Rosetta Stone Bot",
                "=" * 60,
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")

        return report_path

    def get_status_summary(self) -> str:
        """
        Get a short status summary.

        Returns:
            Status string
        """
        status = "✅ COMPLETADO" if self.is_complete else "⏳ EN PROGRESO"
        return (
            f"[{status}] {self._data.total_formatted} / {self._target_hours:.0f}h "
            f"({self.progress_percent:.1f}%) - {len(self._data.sessions)} sesiones"
        )

    # ==================== Utilities ====================

    def _sanitize_email(self, email: str) -> str:
        """Sanitize email for use as key."""
        return email.lower().strip()

    def _cleanup_on_exit(self) -> None:
        """Cleanup handler for unexpected exits."""
        if self._session_start:
            try:
                self._logger.warn("Guardando sesión por cierre inesperado...")
                self.end_session()
            except Exception as e:
                self._logger.error(f"Error en cleanup: {e}")


# ==================== Convenience Functions ====================


def get_user_status(user_email: str, data_dir: str = "data") -> Optional[str]:
    """
    Get status for a user without starting a session.

    Args:
        user_email: User email
        data_dir: Data directory

    Returns:
        Status string or None if user not found
    """
    tracker = TimeTracker(user_email, data_dir=data_dir)
    if tracker.session_count > 0:
        return tracker.get_status_summary()
    return None


def list_all_users(data_dir: str = "data") -> List[Dict[str, Any]]:
    """
    List all tracked users with their status.

    Args:
        data_dir: Data directory

    Returns:
        List of user status dictionaries
    """
    data_file = Path(data_dir) / TimeTracker.DATA_FILE_NAME

    if not data_file.exists():
        return []

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            all_data = json.load(f)

        users = []
        for email, data in all_data.items():
            total_hours = data["total_seconds"] / 3600
            target = data["target_hours"]
            users.append(
                {
                    "email": email,
                    "total_hours": round(total_hours, 2),
                    "target_hours": target,
                    "progress_percent": round((total_hours / target) * 100, 1),
                    "sessions": len(data["sessions"]),
                    "completed": data.get("completed", False),
                }
            )

        return sorted(users, key=lambda x: x["total_hours"], reverse=True)

    except (json.JSONDecodeError, IOError):
        return []
