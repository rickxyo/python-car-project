from unittest.mock import patch

from django.test import TestCase

from cars.models import Brand, Car


class CarDescriptionSignalTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Toyota')

    @patch('cars.signals.get_car_ai_description', return_value='Fast, reliable sedan with great fuel economy.')
    def test_pre_save_generates_description_when_missing(self, get_description_mock):
        car = Car.objects.create(
            model='Corolla',
            brand=self.brand,
            model_year=2024,
            value=35000,
            description='',
        )

        car.refresh_from_db()

        get_description_mock.assert_called_once_with('Corolla', self.brand, 2024)
        self.assertEqual(car.description, 'Fast, reliable sedan with great fuel economy.')

    @patch('cars.signals.get_car_ai_description')
    def test_pre_save_does_not_generate_when_description_already_exists(self, get_description_mock):
        car = Car.objects.create(
            model='Hilux',
            brand=self.brand,
            model_year=2024,
            value=50000,
            description='Already written by user.',
        )

        car.refresh_from_db()

        get_description_mock.assert_not_called()
        self.assertEqual(car.description, 'Already written by user.')

    @patch('cars.signals.get_car_ai_description', return_value='   ')
    def test_pre_save_ignores_empty_ai_response(self, get_description_mock):
        car = Car.objects.create(
            model='Yaris',
            brand=self.brand,
            model_year=2022,
            value=25000,
            description='',
        )

        car.refresh_from_db()

        get_description_mock.assert_called_once_with('Yaris', self.brand, 2022)
        self.assertFalse(car.description)

    @patch('cars.signals.get_car_ai_description', return_value=None)
    def test_pre_save_keeps_empty_description_when_ai_returns_none(self, get_description_mock):
        car = Car.objects.create(
            model='Etios',
            brand=self.brand,
            model_year=2021,
            value=22000,
            description='',
        )

        car.refresh_from_db()

        get_description_mock.assert_called_once_with('Etios', self.brand, 2021)
        self.assertFalse(car.description)
