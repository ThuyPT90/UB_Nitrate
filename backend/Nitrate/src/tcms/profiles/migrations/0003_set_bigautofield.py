# Generated by Django 3.2.12 on 2022-05-08 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_remove_bookmark"),
    ]

    operations = [
        migrations.AlterField(
            model_name="groups",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="usergroupmap",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
