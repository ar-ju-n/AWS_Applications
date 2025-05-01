class Payment(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_payments')
    psychiatrist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='psychiatrist_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment from {self.patient.username} to {self.psychiatrist.username} - {self.amount}"

class PsychiatristProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 