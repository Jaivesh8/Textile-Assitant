from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class Supplier(models.Model):
    name = models.CharField(max_length=255)
    material=models.CharField(max_length=255)
    process=models.CharField(max_length=255)
    address=models.TextField()
    city=models.CharField(max_length=255)
    state=models.CharField(max_length=255)
    latitude=models.FloatField()
    longitude=models.FloatField()
    contact=models.CharField(max_length=255,blank=True,null=True)

    def __str__(self):
        return f"{self.name} - {self.material}"
    from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
   
    email = models.EmailField(unique=True)  # Making email required and unique
    
    # Add any additional fields you need
    # phone_number = models.CharField(max_length=15, blank=True)
    # date_of_birth = models.DateField(null=True, blank=True)
    
    # Set email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # Username is still required by AbstractUser
    
    def __str__(self):
        return self.email