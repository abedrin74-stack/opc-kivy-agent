import os
# Защита Android: отключаем тяжелое шифрование Rust/Crypto
os.environ["ASYNCUA_NO_CRYPTO"] = "1"  

import asyncio
import logging
from asyncua import Client
from asyncua.ua import UaError
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpcAgent")

# Укажите актуальный IP вашего компьютера с MasterOPC
SERVER_URL = "opc.tcp://192.168.1.62:54000"
POLL_INTERVAL = 0.2  # 5 опросов в секунду
MAX_RECONNECT_ATTEMPTS = 5

TAGS = {
    "Saw_Value": "ns=1;s=PN_SIMULATOR.PD_SIMULATOR.Saw",
    "Sin_Value": "ns=1;s=PN_SIMULATOR.PD_SIMULATOR.Sin"
}

class OpcMobileAgentApp(App):
    def build(self):
        self.running = True
        self.client = None 
        self.reconnect_count = 0  
        self.network_task = None
        
        # Создание интерфейса
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.status_label = Label(text="Status: Waiting for start...", font_size="20sp", size_hint_y=None, height="50dp", color=(1, 1, 0, 1))
        self.saw_label = Label(text="Saw (Value): ---", font_size="18sp")
        self.sin_label = Label(text="Sin (Value): ---", font_size="18sp")
        
        layout.add_widget(self.status_label)
        layout.add_widget(self.saw_label)
        layout.add_widget(self.sin_label)

        self.btn = Button(text="Manual Reconnect", size_hint=(None, None), size=("250dp", "50dp"), pos_hint={"center_x": 0.5})
        self.btn.bind(on_press=self.manual_reconnect)
        layout.add_widget(self.btn)

        # Пауза 2 секунды для прорисовки интерфейса на Xiaomi (MIUI) перед пуском сети
        Clock.schedule_once(self.safe_async_start, 2)
        return layout

    def safe_async_start(self, dt):
        logger.info("UI отрисован. Запуск асинхронной задачи в главном цикле.")
        self.update_interface_status("ONLINE LOOP STARTED", (1, 1, 0, 1))
        # Запускаем корутину внутри родного цикла Kivy без создания Thread
        self.network_task = asyncio.ensure_future(self.poll_opc_loop())

    async def poll_opc_loop(self):
        while self.running:
            # Защита батареи при долгой потере связи
            if self.reconnect_count >= MAX_RECONNECT_ATTEMPTS:
                self.update_interface_status("LOST (AUTO RETRY IN 20S)", (1, 0, 0, 1))
                logger.warning("Режим сна 20 секунд...")
                await asyncio.sleep(20)
                self.reconnect_count = 0  
                continue

            try:
                if not self.client:
                    logger.info(f"Подключение... Попытка {self.reconnect_count + 1}")
                    self.update_interface_status("CONNECTING...", (1, 1, 0, 1))
                    self.client = Client(url=SERVER_URL)
                    await asyncio.wait_for(self.client.connect(), timeout=4.0)
                    
                    logger.info("Успешно подключено!")
                    self.update_interface_status("ONLINE", (0, 1, 0, 1))
                    self.reconnect_count = 0  

                while self.running and self.reconnect_count < MAX_RECONNECT_ATTEMPTS:
                    try:
                        # Чтение тегов напрямую без Clock.schedule_once
                        node_saw = self.client.get_node(TAGS["Saw_Value"])
                        val_saw = await asyncio.wait_for(node_saw.read_value(), timeout=0.5)
                        self.update_tag_value("saw", val_saw)

                        node_sin = self.client.get_node(TAGS["Sin_Value"])
                        val_sin = await asyncio.wait_for(node_sin.read_value(), timeout=0.5)
                        self.update_tag_value("sin", val_sin)
                        
                        await asyncio.sleep(POLL_INTERVAL)

                    except (asyncio.TimeoutError, UaError) as inner_e:
                        logger.error(f"Сбой при чтении тегов: {inner_e}")
                        raise inner_e 
                
            except (asyncio.TimeoutError, Exception) as e:
                self.reconnect_count += 1
                logger.error(f"Ошибка сессии (Попытка {self.reconnect_count}): {e}")
                
                self.update_interface_status("RECONNECTING...", (1, 0.5, 0, 1))
                self.update_tag_value("saw", "---")
                self.update_tag_value("sin", "---")
                
                if self.client:
                    try: 
                        await self.client.disconnect()
                    except: 
                        pass
                    self.client = None
                
                await asyncio.sleep(2 + self.reconnect_count)

    def manual_reconnect(self, instance):
        logger.info("Ручной сброс связи.")
        self.reconnect_count = 0
        self.update_interface_status("MANUAL RESET...", (1, 1, 0, 1))
        if self.network_task:
            self.network_task.cancel()
        if self.client:
            # Безопасное отключение в фоне
            asyncio.ensure_future(self.client.disconnect())
            self.client = None
        self.network_task = asyncio.ensure_future(self.poll_opc_loop())

    def update_interface_status(self, text, color):
        # Безопасное обновление: мы в одном потоке с UI
        self.status_label.text = f"Status: {text}"
        self.status_label.color = color

    def update_tag_value(self, tag_type, value):
        if isinstance(value, float):
            value = round(value, 3)
        if tag_type == "saw":
            self.saw_label.text = f"Saw: {value}"
        elif tag_type == "sin":
            self.sin_label.text = f"Sin: {value}"

    def on_stop(self):
        self.running = False
        if self.network_task:
            self.network_task.cancel()

if __name__ == "__main__":
    # Запуск Kivy через нативный асинхронный метод
    loop = asyncio.get_event_loop()
    loop.run_until_complete(OpcMobileAgentApp().async_run(async_lib='asyncio'))
