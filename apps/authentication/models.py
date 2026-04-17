from django.conf import settings
from django.db import models

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('upload_data', 'Upload Data'),
        ('train_model', 'Train Model'),
        ('predict', 'Predict Placement'),
        ('user_register', 'User Register'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        user_label = self.user.username if self.user else 'Anonymous'
        return f'{user_label} - {self.action} @ {self.created_at:%Y-%m-%d %H:%M}'
