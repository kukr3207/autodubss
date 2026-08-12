from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="userbnfuturesrelation",
            name="number_of_lots",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="userbnoptionsrelation",
            name="number_of_lots",
            field=models.PositiveIntegerField(),
        ),
    ]
