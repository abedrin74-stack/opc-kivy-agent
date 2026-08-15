from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
import random

class SimpleTestApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.label = Label(
            text="Тестовое приложение",
            font_size="20sp"
        )
        layout.add_widget(self.label)
        
        self.value_label = Label(
            text="Значение: ---",
            font_size="18sp"
        )
        layout.add_widget(self.value_label)
        
        btn = Button(
            text="Обновить значение",
            size_hint=(None, None),
            size=("200dp", "50dp"),
            pos_hint={"center_x": 0.5}
        )
        btn.bind(on_press=self.update_value)
        layout.add_widget(btn)
        
        # Автообновление каждую секунду
        Clock.schedule_interval(self.auto_update, 1.0)
        
        return layout
    
    def update_value(self, instance):
        self.value_label.text = f"Значение: {random.randint(1, 100)}"
    
    def auto_update(self, dt):
        self.value_label.text = f"Значение: {random.randint(1, 100)}"

if __name__ == "__main__":
    SimpleTestApp().run()
