"""Real-time AI thought dashboard for visualizing AI reasoning."""

from pathlib import Path
from typing import Any
import json


class AIDashboard:
    """Real-time AI thought dashboard."""

    def __init__(self, output_dir: str = "logs/dashboard"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_rooms: dict[str, list[dict]] = {}

    def add_thought(self, room_id: str, thought: dict[str, Any]):
        """Add a thought to the dashboard."""
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = []

        self.active_rooms[room_id].append(thought)
        self._update_dashboard_file(room_id)

    def _update_dashboard_file(self, room_id: str):
        """Update the dashboard HTML file for a room."""
        thoughts = self.active_rooms[room_id]

        html = self._generate_dashboard_html(room_id, thoughts)

        dashboard_file = self.output_dir / f"room_{room_id}.html"
        dashboard_file.write_text(html)

    def _generate_dashboard_html(self, room_id: str, thoughts: list[dict]) -> str:
        """Generate HTML dashboard showing AI thoughts."""
        # Group by phase/round
        grouped = {}
        for thought in thoughts:
            key = f"Round {thought.get('round', '?')} - {thought.get('phase', '?')}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(thought)

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            f"<title>AI Thoughts - Room {room_id}</title>",
            "<style>",
            "body { font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }",
            ".phase { border: 1px solid #444; margin: 10px 0; padding: 10px; }",
            ".thought { margin: 10px 0; padding: 10px; background: #2d2d2d; border-left: 3px solid #007acc; }",
            ".player { color: #4ec9b0; font-weight: bold; }",
            ".reasoning { color: #ce9178; margin: 5px 0; white-space: pre-wrap; }",
            ".choice { color: #b5cea8; }",
            ".timestamp { color: #858585; font-size: 0.9em; }",
            ".notes { background: #252525; padding: 10px; margin: 5px 0; border-left: 3px solid #d7ba7d; white-space: pre-wrap; }",
            ".decision-type { color: #569cd6; font-weight: bold; }",
            "</style>",
            "<meta http-equiv='refresh' content='2'>",  # Auto-refresh every 2s
            "</head><body>",
            f"<h1>AI Thoughts Dashboard - Room {room_id}</h1>",
            f"<p style='color: #858585;'>Total thoughts: {len(thoughts)} | Auto-refreshes every 2 seconds</p>",
        ]

        for phase_label, phase_thoughts in grouped.items():
            html_parts.append(f"<div class='phase'><h2>{phase_label}</h2>")

            for thought in phase_thoughts:
                player = thought.get('player_name', 'Unknown')
                event_type = thought.get('event_type')
                decision_type = thought.get('decision_type', 'action')
                reasoning = thought.get('reasoning', '')
                choice = thought.get('choice', '')
                timestamp = thought.get('timestamp', '')
                notes = thought.get('notes', '')

                html_parts.append(f"<div class='thought'>")
                html_parts.append(f"<div class='player'>{player}</div>")
                html_parts.append(f"<div class='timestamp'>{timestamp}</div>")

                if event_type == 'notes_update':
                    html_parts.append(f"<div class='decision-type'>📝 Notes Update</div>")
                    if notes:
                        html_parts.append(f"<div class='notes'>{notes}</div>")
                else:
                    html_parts.append(f"<div class='decision-type'>🎯 {decision_type}</div>")
                    if reasoning:
                        html_parts.append(f"<div class='reasoning'>💭 {reasoning}</div>")
                    if choice:
                        html_parts.append(f"<div class='choice'>→ {choice}</div>")

                html_parts.append("</div>")

            html_parts.append("</div>")

        html_parts.append("</body></html>")
        return "\n".join(html_parts)

    def clear_room(self, room_id: str):
        """Clear dashboard for a room."""
        if room_id in self.active_rooms:
            del self.active_rooms[room_id]

        dashboard_file = self.output_dir / f"room_{room_id}.html"
        if dashboard_file.exists():
            dashboard_file.unlink()
