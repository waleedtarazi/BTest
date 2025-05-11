from django.db import models
# Create your models here.

class Todo(models.Model):
    title: models.CharField(max_length=50)
    completed: models.BooleanField(default=False)

    def __str__(self):
        return f"title: {self.title}"

