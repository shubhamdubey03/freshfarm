from django.db import models
from core_app.models import *

# Create your models here.
class Category(models.Model):
    CATEGORY_TYPE = (
        ("grocery", "Grocery"),      # → vendor flow
        ("vegetable", "Vegetable"),  # → farmer flow
    )
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="categories")
    category_type = models.CharField(
        max_length=20, 
        choices=CATEGORY_TYPE, 
        default="vegetable"
    )                

class Product(models.Model):

    seller = models.ForeignKey(
        "core_app.Seller",
        on_delete=models.CASCADE,
        related_name="products"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="products/")

    created_at = models.DateTimeField(auto_now_add=True)


class ProductVariant(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    unit = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    stock = models.IntegerField()
    harvest_date = models.DateField()

class CartItem(models.Model):

    user = models.ForeignKey("core_app.User", on_delete=models.CASCADE)
    variant = models.ForeignKey("core_product.ProductVariant", on_delete=models.CASCADE)

    quantity = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)