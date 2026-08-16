import asyncio
from threading import Thread
import logging
from asyncua import Client
from asyncua.ua import UaError
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OpcAgent")

SERVER_URL = "opc.tcp://192.168.1.62:54000"
POLL_INTERVAL = 0.2  
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
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.status_label = Label(text="Status: Init Thread...", font_size="20sp", size_hint_y=None, height="50dp", color=(1, 1, 0, 1))
        self.saw_label = Label(text="Saw (Value): ---", font_size="18sp")
        self.sin_label = Label(text="Sin (Value): ---", font_size="18sp")
        
        layout.add_widget(self.status_label)
        layout.add_widget(self.saw_label)
        layout.add_widget(self.sin_label)

        self.btn = Button(text="Manual Reconnect", size_hint=(None, None), size=("250dp", "50dp"), pos_hint={"center_x": 0.5})
        self.btn.bind(on_press=self.manual_reconnect)
        layout.add_widget(self.btn)

        self.worker_thread = Thread(target=self.start_async_loop, daemon=True)
        self.worker_thread.start()

        return layout

    def start_async_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.poll_opc_loop())

    async def poll_opc_loop(self):
        while self.running:
            if self.reconnect_count >= MAX_RECONNECT_ATTEMPTS:
                Clock.schedule_once(lambda dt: self.update_interface_status("LOST (AUTO RETRY IN 20S)", (1, 0, 0, 1)))
                logger.warning("Режим сна 20 секунд...")
                await asyncio.sleep(20)
                self.reconnect_count = 0  
                continue

            try:
                if not self.client:
                    logger.info(f"Подключение... Попытка {self.reconnect_count + 1}")
                    Clock.schedule_once(lambda dt: self.update_interface_status("CONNECTING...", (1, 1, 0, 1)))
                    self.client = Client(url=SERVER_URL)
                    await asyncio.wait_for(self.client.connect(), timeout=4.0)
                    
                    logger.info("Успешно подключено!")
                    Clock.schedule_once(lambda dt: self.update_interface_status("ONLINE", (0, 1, 0, 1)))
                    self.reconnect_count = 0  

                while self.running and self.reconnect_count < MAX_RECONNECT_ATTEMPTS:
                    try:
                        node_saw = self.client.get_node(TAGS["Saw_Value"])
                        val_saw = await asyncio.wait_for(node_saw.read_value(), timeout=0.5)
                        Clock.schedule_once(lambda dt, v=val_saw: self.update_tag_value("saw", v))

                        node_sin = self.client.get_node(TAGS["Sin_Value"])
                        val_sin = await asyncio.wait_for(node_sin.read_value(), timeout=0.5)
                        Clock.schedule_once(lambda dt, v=val_sin: self.update_tag_value("sin", v))
                        
                        await asyncio.sleep(POLL_INTERVAL)

                    except (asyncio.TimeoutError, UaError) as inner_e:
                        logger.error(f"Сбой при чтении тегов: {inner_e}")
                        raise inner_e 
                
            except (asyncio.TimeoutError, Exception) as e:
                self.reconnect_count += 1
                logger.error(f"Ошибка сессии (Попытка {self.reconnect_count}): {e}")
                
                Clock.schedule_once(lambda dt: self.update_interface_status("RECONNECTING...", (1, 0.5, 0, 1)))
                Clock.schedule_once(lambda dt: self.update_tag_value("saw", "---"))
                Clock.schedule_once(lambda dt: self.update_tag_value("sin", "---"))
                
                if self.client:
                    try: await self.client.disconnect()
                    except: pass
                    self.client = None
                
                await asyncio.sleep(2 + self.reconnect_count)

    def manual_reconnect(self, instance):
        logger.info("Ручной сброс связи.")
        self.reconnect_count = 0
        Clock.schedule_once(lambda dt: self.update_interface_status("CONNECTING...", (1, 1, 0, 1)))

    def update_interface_status(self, text, color):
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

if __name__ == "__main__":
    OpcMobileAgentApp().run()
