import threading
import time
from datetime import datetime, time as dt_time
import yaml


class AlarmScheduler:
    def __init__(self, config, activate_callback, deactivate_callback):
        """
        Programador de alarmas

        Args:
            config: Diccionario de configuración
            activate_callback: Función a llamar para activar alarma
            deactivate_callback: Función a llamar para desactivar alarma
        """
        self.config = config
        self.activate_callback = activate_callback
        self.deactivate_callback = deactivate_callback
        self.running = True
        self.last_state = None
        self.manual_override = False
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        print("Programador de alarmas iniciado")

    def set_manual_override(self, enabled):
        """Establecer control manual (desactiva programación automática temporalmente)"""
        self.manual_override = enabled
        if enabled:
            print(" Control manual activado - programación automática deshabilitada")
        else:
            print(" Control automático restaurado")

    def should_be_active(self):
        """Verificar si la alarma debería estar activa según los horarios"""
        if not self.config.get("schedule", {}).get("auto_schedule", False):
            return None  # Programación automática desactivada

        if self.manual_override:
            return None  # Control manual activo

        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()  # 0=Lunes, 6=Domingo

        schedules = self.config.get("schedule", {}).get("schedules", [])

        for schedule in schedules:
            if not schedule.get("enabled", True):
                continue

            # Verificar si el día actual está en el horario
            if current_day not in schedule.get("days", []):
                continue

            # Parsear horarios
            start_str = schedule.get("start_time", "22:00")
            end_str = schedule.get("end_time", "06:00")

            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()

            # Verificar si estamos en el rango horario
            if start_time <= end_time:
                # Rango normal (ej: 09:00 - 17:00)
                if start_time <= current_time <= end_time:
                    return True
            else:
                # Rango que cruza medianoche (ej: 22:00 - 06:00)
                if current_time >= start_time or current_time <= end_time:
                    return True

        return False

    def _scheduler_loop(self):
        """Loop principal del programador"""
        while self.running:
            try:
                should_activate = self.should_be_active()

                # Si hay un cambio de estado y no estamos en control manual
                if should_activate is not None and should_activate != self.last_state:
                    if should_activate:
                        print(" [PROGRAMACIÓN] Activando alarma automáticamente")
                        self.activate_callback()
                    else:
                        print(" [PROGRAMACIÓN] Desactivando alarma automáticamente")
                        self.deactivate_callback()

                    self.last_state = should_activate

                # Verificar cada 30 segundos
                time.sleep(30)

            except Exception as e:
                print(f"❌ Error en programador: {e}")
                time.sleep(60)

    def get_next_schedule(self):
        """Obtener información del próximo cambio de estado"""
        if not self.config.get("schedule", {}).get("auto_schedule", False):
            return None

        now = datetime.now()
        current_time = now.time()
        current_day = now.weekday()

        schedules = self.config.get("schedule", {}).get("schedules", [])
        next_changes = []

        for schedule in schedules:
            if not schedule.get("enabled", True):
                continue

            for day in schedule.get("days", []):
                start_str = schedule.get("start_time", "22:00")
                end_str = schedule.get("end_time", "06:00")

                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()

                # Calcular días hasta el próximo evento
                days_until = (day - current_day) % 7

                next_changes.append({
                    'name': schedule.get('name', 'Sin nombre'),
                    'action': 'activar',
                    'time': start_str,
                    'days_until': days_until,
                    'day_name': self._get_day_name(day)
                })

                next_changes.append({
                    'name': schedule.get('name', 'Sin nombre'),
                    'action': 'desactivar',
                    'time': end_str,
                    'days_until': days_until,
                    'day_name': self._get_day_name(day)
                })

        # Ordenar por proximidad
        next_changes.sort(key=lambda x: x['days_until'])

        return next_changes[:3] if next_changes else []

    def _get_day_name(self, day_num):
        """Convertir número de día a nombre"""
        days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return days[day_num]

    def stop(self):
        """Detener el programador"""
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=5)
        print(" Programador de alarmas detenido")