# -*- coding: utf-8 -*-
import time
import json
from locust import task
from locust_plugins.users import SocketIOUser


class MySocketIOUser(SocketIOUser):
    response = None

    @task
    def my_task(self):
        self.response = None

        self.connect("ws://153.92.223.240:8080")

        # example of subscribe
        self.send('42["subscribe",{"url":"/", "sendInitialUpdate": true}]')
        # self.send(json.dumps({"action": "chat_message", "message": "test"}))

        # wait until I get a push message to on_message
        while not self.response:
            time.sleep(0.1)

        # wait for additional pushes, while occasionally sending heartbeats, like a real client would
        self.send(json.dumps({"action": "chat_message", "message": "test"}))
        self.sleep_with_heartbeat(45)

    def on_message(self, message):
        self.response = json.loads(message)


if __name__ == "__main__":
    host = "http://153.92.223.240"
