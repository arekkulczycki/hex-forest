# -*- coding: utf-8 -*-
from locust import HttpUser, task


class MyHttpUser(HttpUser):
    @task
    def hello_world(self):
        self.client.get("/")
        self.client.get("/analysis")
