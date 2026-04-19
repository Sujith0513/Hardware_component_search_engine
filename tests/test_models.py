"""
test_models.py - Unit tests for Pydantic models.

Tests validation, serialization, and edge cases for all data models.
"""

import pytest
from datetime import datetime
from src.state import (
    PinInfo,
    DatasheetInfo,
    PricingEntry,
    StockStatus,
    ComponentReport,
)


class TestPinInfo:
    def test_valid_pin(self):
        pin = PinInfo(pin_name="GPIO0", pin_number="1", function="General Purpose I/O")
        assert pin.pin_name == "GPIO0"
        assert pin.pin_number == "1"
        assert pin.function == "General Purpose I/O"

    def test_missing_field(self):
        with pytest.raises(Exception):
            PinInfo(pin_name="GPIO0")  # missing pin_number and function


class TestDatasheetInfo:
    def test_valid_datasheet(self):
        info = DatasheetInfo(
            manufacturer="Espressif Systems",
            datasheet_url="https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf",
            description="Wi-Fi & Bluetooth MCU module",
            key_pins=[
                PinInfo(pin_name="VCC", pin_number="2", function="Power Supply 3.3V"),
            ],
            package_type="SMD Module",
            operating_voltage="2.2V - 3.6V",
        )
        assert info.manufacturer == "Espressif Systems"
        assert len(info.key_pins) == 1

    def test_empty_pins_rejected(self):
        with pytest.raises(Exception):
            DatasheetInfo(
                manufacturer="Test",
                datasheet_url="https://example.com/ds.pdf",
                description="Test",
                key_pins=[],  # min_length=1
            )

    def test_optional_fields_none(self):
        info = DatasheetInfo(
            manufacturer="Test",
            datasheet_url="https://example.com/ds.pdf",
            description="Test component",
            key_pins=[PinInfo(pin_name="VCC", pin_number="1", function="Power")],
        )
        assert info.package_type is None
        assert info.operating_voltage is None


class TestPricingEntry:
    def test_valid_entry(self):
        entry = PricingEntry(
            distributor="Mouser Electronics",
            unit_price=2.80,
            moq=1,
            stock_quantity=14523,
            url="https://www.mouser.com/test",
        )
        assert entry.distributor == "Mouser Electronics"
        assert entry.unit_price == 2.80

    def test_negative_price_rejected(self):
        with pytest.raises(Exception):
            PricingEntry(
                distributor="Test",
                unit_price=-1.0,  # ge=0
                moq=1,
                stock_quantity=100,
                url="https://test.com",
            )

    def test_zero_moq_rejected(self):
        with pytest.raises(Exception):
            PricingEntry(
                distributor="Test",
                unit_price=1.0,
                moq=0,  # ge=1
                stock_quantity=100,
                url="https://test.com",
            )

    def test_zero_price_allowed(self):
        """Zero price is allowed (free samples exist)."""
        entry = PricingEntry(
            distributor="Test",
            unit_price=0.0,
            moq=1,
            stock_quantity=100,
            url="https://test.com",
        )
        assert entry.unit_price == 0.0


class TestStockStatus:
    def test_in_stock(self):
        status = StockStatus(
            in_stock=True,
            total_stock_across_distributors=26653,
            best_price=2.80,
            best_distributor="Mouser Electronics",
        )
        assert status.in_stock is True

    def test_out_of_stock(self):
        status = StockStatus(
            in_stock=False,
            total_stock_across_distributors=0,
            best_price=0.0,
            best_distributor="N/A",
        )
        assert status.in_stock is False


class TestComponentReport:
    def test_valid_report(self):
        report = ComponentReport(
            component_name="ESP32-WROOM-32",
            manufacturer="Espressif Systems",
            datasheet_url="https://example.com/ds.pdf",
            description="Wi-Fi & BT MCU",
            key_pins_summary=[
                PinInfo(pin_name="VCC", pin_number="2", function="Power"),
            ],
            average_price=3.12,
            price_range="$2.80 - $3.45",
            pricing_breakdown=[
                PricingEntry(
                    distributor="Mouser",
                    unit_price=2.80,
                    moq=1,
                    stock_quantity=14523,
                    url="https://mouser.com/test",
                ),
            ],
            in_stock=True,
            total_available_stock=26653,
            best_deal="Mouser @ $2.80 (MOQ: 1)",
            package_type="SMD Module",
            operating_voltage="2.2V - 3.6V",
        )
        assert report.component_name == "ESP32-WROOM-32"
        assert report.in_stock is True

    def test_report_serialization(self):
        report = ComponentReport(
            component_name="NE555",
            manufacturer="Texas Instruments",
            datasheet_url="https://example.com/ne555.pdf",
            description="Timer IC",
            key_pins_summary=[
                PinInfo(pin_name="GND", pin_number="1", function="Ground"),
            ],
            average_price=0.45,
            price_range="$0.38 - $0.55",
            pricing_breakdown=[],
            in_stock=True,
            total_available_stock=290000,
            best_deal="Mouser @ $0.38 (MOQ: 1)",
        )
        # Test JSON serialization
        json_data = report.model_dump()
        assert isinstance(json_data, dict)
        assert "component_name" in json_data
        assert "timestamp" in json_data

    def test_report_with_empty_optional_fields(self):
        report = ComponentReport(
            component_name="Unknown Part",
            manufacturer="Unknown",
            datasheet_url="Not found",
            description="Could not find info",
            key_pins_summary=[],
            average_price=0.0,
            price_range="N/A",
            pricing_breakdown=[],
            in_stock=False,
            total_available_stock=0,
            best_deal="Data incomplete",
        )
        assert report.package_type is None
        assert report.operating_voltage is None
        assert len(report.agent_reasoning_trace) == 0


class TestModelIntegration:
    """Test that models work together as expected in the pipeline."""

    def test_pricing_to_stock_validation(self):
        """Simulate the pricing -> stock validation flow."""
        from src.tools.stock_validator import validate_stock

        entries = [
            PricingEntry(
                distributor="Mouser",
                unit_price=2.80,
                moq=1,
                stock_quantity=14523,
                url="https://mouser.com/test",
            ),
            PricingEntry(
                distributor="DigiKey",
                unit_price=3.10,
                moq=1,
                stock_quantity=8920,
                url="https://digikey.com/test",
            ),
        ]

        status = validate_stock(entries)
        assert status.in_stock is True
        assert status.total_stock_across_distributors == 23443
        assert status.best_price == 2.80
        assert status.best_distributor == "Mouser"

    def test_empty_pricing_stock_validation(self):
        from src.tools.stock_validator import validate_stock

        status = validate_stock([])
        assert status.in_stock is False
        assert status.total_stock_across_distributors == 0
