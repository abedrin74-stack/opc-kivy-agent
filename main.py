import asyncio
from threading import Thread
from asyncua import Client
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

# Настройки строго как в вашем успешном тесте
SERVER_URL = "opc.tcp://192.168.1.62:54000"
POLL_INTERVAL = 1.0

TAGS = {
    "Saw_Value": "ns=1;s=PN_SIMULATOR.PD_SIMULATOR.Saw",
    "Sin_Value": "ns=1;s=PN_SIMULATOR.PD_SIMULATOR.Sin"
}

class OpcMobileAgentApp(App):
    def build(self):
        self.running = True
        
        # Задаем вертикальный слой с отступами
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        # 1. Верхний статус подключения
        self.status_label = Label(
            text="Статус: Попытка подключения...", 
            font_size="20sp", 
            size_hint_y=None, 
            height="50dp",
            color=(1, 1, 0, 1) # Желтый по умолчанию
        )
        layout.add_widget(self.status_label)

        # 2. Метки для красивого вывода тегов
        self.saw_label = Label(text="Пила (Saw): ---", font_size="18sp")
        self.sin_label = Label(text="Синус (Sin): ---", font_size="18sp")
        layout.add_widget(self.saw_label)
        layout.add_widget(self.sin_label)

        # 3. Наша стабильная кнопка (пока просто информационная)
        self.btn = Button(
            text="Агент активен",
            size_hint=(None, None),
            size=("200dp", "50dp"),
            pos_hint={"center_x": 0.5}
        )
        layout.add_widget(self.btn)

        # Запускаем фоновый поток для работы с сетью (защита от зависания окна)
        self.worker_thread = Thread(target=self.start_async_loop, daemon=True)
        self.worker_thread.start()

        return layout

    def start_async_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.opc_worker())

    async def opc_worker(self):
        was_connected = False
        
        while self.running:
            try:
                client = Client(url=SERVER_URL)
                # Таймаут на подключение
                await asyncio.wait_for(client.connect(), timeout=3.0)
                
                async with client:
                    if not was_connected:
                        # Передаем зеленый статус "СВЯЗЬ ОК" в интерфейс
                        Clock.schedule_once(lambda dt: self.update_interface_status("СВЯЗЬ ОК", (0, 1, 0, 1)))
                        was_connected = True
                    
                    while self.running:
                        # Читаем тег Пилы
                        try:
                            node_saw = client.get_node(TAGS["Saw_Value"])
                            val_saw = await asyncio.wait_for(node_saw.read_value(), timeout=2.0)
                            Clock.schedule_once(lambda dt, v=val_saw: self.update_tag_value("saw", v))
                        except Exception:
                            Clock.schedule_once(lambda dt: self.update_tag_value("saw", "ОШИБКА"))

                        # Читаем тег Синуса
                        try:
                            node_sin = client.get_node(TAGS["Sin_Value"])
                            val_sin = await asyncio.wait_for(node_sin.read_value(), timeout=2.0)
                            Clock.schedule_once(lambda dt, v=val_sin: self.update_tag_value("sin", v))
                        except Exception:
                            Clock.schedule_once(lambda dt: self.update_tag_value("sin", "ОШИБКА"))

                        await asyncio.sleep(POLL_INTERVAL)
                        
            except (asyncio.TimeoutError, Exception):
                if was_connected:
                    was_connected = False
                # Если MasterOPC упал — выводим красный статус ошибки
                Clock.schedule_once(lambda dt: self.update_interface_status("ОТКЛЮЧЕН / УПАЛ", (1, 0, 0, 1)))
                Clock.schedule_once(lambda dt: self.update_tag_value("saw", "---"))
                Clock.schedule_once(lambda dt: self.update_tag_value("sin", "---"))
                await asyncio.sleep(3)

    # Функции безопасной передачи данных из фона на экран телефона/ПК
    def update_interface_status(self, text, color):
        self.status_label.text = f"Статус: {text}"
        self.status_label.color = color

    def update_tag_value(self, tag_type, value):
        if isinstance(value, float):
            value = round(value, 3) # Округляем длинный синус, как в вашем скрипте
            
        if tag_type == "saw":
            self.saw_label.text = f"Пила (Saw): {value}"
        elif tag_type == "sin":
            self.sin_label.text = f"Синус (Sin): {value}"

    def on_stop(self):
        # Корректно завершаем фоновый поток при закрытии приложения
        self.running = False

if __name__ == "__main__":
    OpcMobileAgentApp().run()
