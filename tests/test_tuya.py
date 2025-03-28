"""Tests for Tuya quirks."""

import asyncio
import datetime
from unittest import mock

import pytest
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice, get_device
import zigpy.types as t
from zigpy.zcl import foundation

import zhaquirks
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OFF,
    ON,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZONE_STATE,
)
from zhaquirks.tuya import Data, TuyaManufClusterAttributes
import zhaquirks.tuya.ts0042
import zhaquirks.tuya.ts0043
import zhaquirks.tuya.ts0601_electric_heating
import zhaquirks.tuya.ts0601_motion
import zhaquirks.tuya.ts0601_siren
import zhaquirks.tuya.ts0601_trv

from tests.common import ClusterListener

zhaquirks.setup()

ZCL_TUYA_SET_TIME_REQUEST = b"\tp\x24\x00\00"

ZCL_TUYA_MOTION = b"\tL\x01\x00\x05\x03\x04\x00\x01\x02"
ZCL_TUYA_SWITCH_ON = b"\tQ\x02\x006\x01\x01\x00\x01\x01"
ZCL_TUYA_SWITCH_OFF = b"\tQ\x02\x006\x01\x01\x00\x01\x00"
ZCL_TUYA_ATTRIBUTE_617_TO_179 = b"\tp\x02\x00\x02i\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_SIREN_TEMPERATURE = ZCL_TUYA_ATTRIBUTE_617_TO_179
ZCL_TUYA_SIREN_HUMIDITY = b"\tp\x02\x00\x02j\x02\x00\x04\x00\x00\x00U"
ZCL_TUYA_SIREN_ON = b"\t\t\x02\x00\x04h\x01\x00\x01\x01"
ZCL_TUYA_SIREN_OFF = b"\t\t\x02\x00\x04h\x01\x00\x01\x00"
ZCL_TUYA_VALVE_TEMPERATURE = b"\tp\x02\x00\x02\x03\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_VALVE_TARGET_TEMP = b"\t3\x01\x03\x05\x02\x02\x00\x04\x00\x00\x002"
ZCL_TUYA_VALVE_OFF = b"\t2\x01\x03\x04\x04\x04\x00\x01\x00"
ZCL_TUYA_VALVE_SCHEDULE = b"\t2\x01\x03\x04\x04\x04\x00\x01\x01"
ZCL_TUYA_VALVE_MANUAL = b"\t2\x01\x03\x04\x04\x04\x00\x01\x02"
ZCL_TUYA_VALVE_COMFORT = b"\t2\x01\x03\x04\x04\x04\x00\x01\x03"
ZCL_TUYA_VALVE_ECO = b"\t2\x01\x03\x04\x04\x04\x00\x01\x04"
ZCL_TUYA_VALVE_BOOST = b"\t2\x01\x03\x04\x04\x04\x00\x01\x05"
ZCL_TUYA_VALVE_COMPLEX = b"\t2\x01\x03\x04\x04\x04\x00\x01\x06"
ZCL_TUYA_VALVE_WINDOW_DETECTION = b"\tp\x02\x00\x02\x68\x00\x00\x03\x01\x10\x05"
ZCL_TUYA_VALVE_WORKDAY_SCHEDULE = b"\tp\x02\x00\x02\x70\x00\x00\x12\x06\x00\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F"
ZCL_TUYA_VALVE_WEEKEND_SCHEDULE = b"\tp\x02\x00\x02\x71\x00\x00\x12\x06\x00\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F"
ZCL_TUYA_VALVE_STATE_50 = b"\t2\x01\x03\x04\x6D\x02\x00\x04\x00\x00\x00\x32"
ZCL_TUYA_VALVE_CHILD_LOCK_ON = b"\t2\x01\x03\x04\x07\x01\x00\x01\x01"
ZCL_TUYA_VALVE_AUTO_LOCK_ON = b"\t2\x01\x03\x04\x74\x01\x00\x01\x01"
ZCL_TUYA_VALVE_BATTERY_LOW = b"\t2\x01\x03\x04\x6E\x01\x00\x01\x01"

ZCL_TUYA_VALVE_ZONNSMART_TEMPERATURE = (
    b"\tp\x01\x00\x02\x18\x02\x00\x04\x00\x00\x00\xd3"
)
ZCL_TUYA_VALVE_ZONNSMART_TARGET_TEMP = (
    b"\t3\x01\x03\x05\x10\x02\x00\x04\x00\x00\x00\xcd"
)
ZCL_TUYA_VALVE_ZONNSMART_HOLIDAY_TEMP = (
    b"\t3\x01\x03\x05\x20\x02\x00\x04\x00\x00\x00\xaa"
)
ZCL_TUYA_VALVE_ZONNSMART_TEMP_OFFSET = (
    b"\t3\x01\x03\x05\x1b\x02\x00\x04\x00\x00\x00\x0b"
)
ZCL_TUYA_VALVE_ZONNSMART_MODE_MANUAL = b"\t2\x01\x03\x04\x02\x04\x00\x01\x01"
ZCL_TUYA_VALVE_ZONNSMART_MODE_SCHEDULE = b"\t2\x01\x03\x04\x02\x04\x00\x01\x00"
ZCL_TUYA_VALVE_ZONNSMART_HEAT_STOP = b"\t2\x01\x03\x04\x6b\x01\x00\x01\x00"

ZCL_TUYA_EHEAT_TEMPERATURE = b"\tp\x02\x00\x02\x18\x02\x00\x04\x00\x00\x00\xb3"
ZCL_TUYA_EHEAT_TARGET_TEMP = b"\t3\x01\x03\x05\x10\x02\x00\x04\x00\x00\x00\x15"


class NewDatetime(datetime.datetime):
    """Override for datetime functions."""

    @classmethod
    def now(cls):
        """Return testvalue."""

        return cls(1970, 1, 1, 1, 0, 0)

    @classmethod
    def utcnow(cls):
        """Return testvalue."""

        return cls(1970, 1, 1, 2, 0, 0)


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_motion.TuyaMotion,))
async def test_motion(zigpy_device_from_quirk, quirk):
    """Test tuya motion sensor."""

    motion_dev = zigpy_device_from_quirk(quirk)

    motion_cluster = motion_dev.endpoints[1].ias_zone
    motion_listener = ClusterListener(motion_cluster)

    tuya_cluster = motion_dev.endpoints[1].tuya_manufacturer

    # send motion on Tuya manufacturer specific cluster
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_MOTION)
    with mock.patch.object(motion_cluster, "reset_s", 0):
        tuya_cluster.handle_message(hdr, args)

    assert len(motion_listener.cluster_commands) == 1
    assert len(motion_listener.attribute_updates) == 1
    assert motion_listener.cluster_commands[0][1] == ZONE_STATE
    assert motion_listener.cluster_commands[0][2][0] == ON

    await asyncio.gather(asyncio.sleep(0), asyncio.sleep(0), asyncio.sleep(0))

    assert len(motion_listener.cluster_commands) == 2
    assert motion_listener.cluster_commands[1][1] == ZONE_STATE
    assert motion_listener.cluster_commands[1][2][0] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaSingleSwitchTI,))
async def test_singleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    switch_listener = ClusterListener(switch_cluster)

    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_ON)
    tuya_cluster.handle_message(hdr, args)
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_OFF)
    tuya_cluster.handle_message(hdr, args)

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaDoubleSwitchTO,))
async def test_doubleswitch_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya double switch."""

    ZCL_TUYA_SWITCH_COMMAND_03 = b"\tQ\x03\x006\x01\x01\x00\x01\x01"
    ZCL_TUYA_SWITCH_EP2_ON = b"\tQ\x02\x006\x02\x01\x00\x01\x01"
    ZCL_TUYA_SWITCH_EP2_OFF = b"\tQ\x02\x006\x02\x01\x00\x01\x00"

    switch_dev = zigpy_device_from_quirk(quirk)

    switch1_cluster = switch_dev.endpoints[1].on_off
    switch1_listener = ClusterListener(switch1_cluster)

    switch2_cluster = switch_dev.endpoints[2].on_off
    switch2_listener = ClusterListener(switch2_cluster)

    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch1_listener.attribute_updates) == 0
    assert len(switch2_listener.cluster_commands) == 0
    assert len(switch2_listener.attribute_updates) == 0

    # events from channel 1 updates only EP 1
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_ON)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 1
    assert len(switch2_listener.attribute_updates) == 0
    assert switch1_listener.attribute_updates[0][0] == 0x0000
    assert switch1_listener.attribute_updates[0][1] == ON

    # events from channel 2 updates only EP 2
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_EP2_ON)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 1
    assert len(switch2_listener.attribute_updates) == 1
    assert switch2_listener.attribute_updates[0][0] == 0x0000
    assert switch2_listener.attribute_updates[0][1] == ON

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_OFF)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 1
    assert switch1_listener.attribute_updates[1][0] == 0x0000
    assert switch1_listener.attribute_updates[1][1] == OFF

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_EP2_OFF)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2
    assert switch2_listener.attribute_updates[1][0] == 0x0000
    assert switch2_listener.attribute_updates[1][1] == OFF

    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0

    # command_id = 0x0003
    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SWITCH_COMMAND_03)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0
    # no switch attribute updated (Unsupported command)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SET_TIME_REQUEST)
    tuya_cluster.handle_message(hdr, args)
    assert len(switch1_listener.cluster_commands) == 0
    assert len(switch2_listener.cluster_commands) == 0
    # no switch attribute updated (TUYA_SET_TIME command)
    assert len(switch1_listener.attribute_updates) == 2
    assert len(switch2_listener.attribute_updates) == 2


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_switch.TuyaSingleSwitchTI,))
async def test_singleswitch_requests(zigpy_device_from_quirk, quirk):
    """Test tuya single switch."""

    switch_dev = zigpy_device_from_quirk(quirk)

    switch_cluster = switch_dev.endpoints[1].on_off
    tuya_cluster = switch_dev.endpoints[1].tuya_manufacturer

    with mock.patch.object(
        tuya_cluster.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as m1:

        status = await switch_cluster.command(0x0000)
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x01\x01\x01\x00\x01\x00",
            expect_reply=True,
            command_id=0,
        )
        assert status == 0

        status = await switch_cluster.command(0x0001)
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x03\x01\x01\x00\x01\x01",
            expect_reply=True,
            command_id=0,
        )
        assert status == 0

    status = await switch_cluster.command(0x0002)
    assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


async def test_tuya_data_conversion():
    """Test tuya conversion from Data to ztype and reverse."""
    assert Data([4, 0, 0, 1, 39]).to_value(t.uint32_t) == 295
    assert Data([4, 0, 0, 0, 220]).to_value(t.uint32_t) == 220
    assert Data([4, 255, 255, 255, 236]).to_value(t.int32s) == -20
    assert Data.from_value(t.uint32_t(295)) == [4, 0, 0, 1, 39]
    assert Data.from_value(t.uint32_t(220)) == [4, 0, 0, 0, 220]
    assert Data.from_value(t.int32s(-20)) == [4, 255, 255, 255, 236]


class TestManufCluster(TuyaManufClusterAttributes):
    """Cluster for synthetic tests."""

    manufacturer_attributes = {617: ("test_attribute", t.uint32_t)}


class TestDevice(CustomDevice):
    """Device for synthetic tests."""

    signature = {
        MODELS_INFO: [("_test_manuf", "_test_device")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TestManufCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [TestManufCluster],
                OUTPUT_CLUSTERS: [],
            }
        },
    }


@pytest.mark.parametrize("quirk", (TestDevice,))
async def test_tuya_receive_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of tuya commands to attributes."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer
    listener = ClusterListener(tuya_cluster)

    hdr, args = tuya_cluster.deserialize(ZCL_TUYA_ATTRIBUTE_617_TO_179)
    tuya_cluster.handle_message(hdr, args)

    assert len(listener.attribute_updates) == 1
    assert listener.attribute_updates[0][0] == 617
    assert listener.attribute_updates[0][1] == 179


@pytest.mark.parametrize("quirk", (TestDevice,))
async def test_tuya_send_attribute(zigpy_device_from_quirk, quirk):
    """Test conversion of attributes to tuya commands."""

    test_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = test_dev.endpoints[1].tuya_manufacturer

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        (status,) = await tuya_cluster.write_attributes({617: 179})
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01i\x02\x00\x04\x00\x00\x00\xb3",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_siren.TuyaSiren,))
async def test_siren_state_report(zigpy_device_from_quirk, quirk):
    """Test tuya siren standard state reporting from incoming commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer

    temp_listener = ClusterListener(siren_dev.endpoints[1].temperature)
    humid_listener = ClusterListener(siren_dev.endpoints[1].humidity)
    switch_listener = ClusterListener(siren_dev.endpoints[1].on_off)

    frames = (
        ZCL_TUYA_SIREN_TEMPERATURE,
        ZCL_TUYA_SIREN_HUMIDITY,
        ZCL_TUYA_SIREN_ON,
        ZCL_TUYA_SIREN_OFF,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(temp_listener.cluster_commands) == 0
    assert len(temp_listener.attribute_updates) == 1
    assert temp_listener.attribute_updates[0][0] == 0x0000
    assert temp_listener.attribute_updates[0][1] == 1790

    assert len(humid_listener.cluster_commands) == 0
    assert len(humid_listener.attribute_updates) == 1
    assert humid_listener.attribute_updates[0][0] == 0x0000
    assert humid_listener.attribute_updates[0][1] == 8500

    assert len(switch_listener.cluster_commands) == 0
    assert len(switch_listener.attribute_updates) == 2
    assert switch_listener.attribute_updates[0][0] == 0x0000
    assert switch_listener.attribute_updates[0][1] == ON
    assert switch_listener.attribute_updates[1][0] == 0x0000
    assert switch_listener.attribute_updates[1][1] == OFF


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_siren.TuyaSiren,))
async def test_siren_send_attribute(zigpy_device_from_quirk, quirk):
    """Test tuya siren outgoing commands."""

    siren_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = siren_dev.endpoints[1].tuya_manufacturer
    switch_cluster = siren_dev.endpoints[1].on_off

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        _, status = await switch_cluster.command(0x0000)
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01h\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await switch_cluster.command(0x0001)
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02h\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await switch_cluster.command(0x0003)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.ZonnsmartTV01_ZG,))
async def test_zonnsmart_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)

    frames = (
        ZCL_TUYA_VALVE_ZONNSMART_TEMPERATURE,
        ZCL_TUYA_VALVE_ZONNSMART_TARGET_TEMP,
        ZCL_TUYA_VALVE_ZONNSMART_HOLIDAY_TEMP,
        ZCL_TUYA_VALVE_ZONNSMART_TEMP_OFFSET,
        ZCL_TUYA_VALVE_ZONNSMART_MODE_MANUAL,
        ZCL_TUYA_VALVE_ZONNSMART_MODE_SCHEDULE,
        ZCL_TUYA_VALVE_ZONNSMART_HEAT_STOP,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 11
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 2110
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 2050
    assert thermostat_listener.attribute_updates[4][0] == 0x0014  # HOLIDAY
    assert thermostat_listener.attribute_updates[4][1] == 1700
    assert thermostat_listener.attribute_updates[5][0] == 0x0010  # OFFSET
    assert thermostat_listener.attribute_updates[5][1] == 110
    assert thermostat_listener.attribute_updates[6][0] == 0x0025  # MANUAL
    assert thermostat_listener.attribute_updates[6][1] == 0
    assert thermostat_listener.attribute_updates[7][0] == 0x4002
    assert thermostat_listener.attribute_updates[7][1] == 1
    assert thermostat_listener.attribute_updates[8][0] == 0x0025  # SCHEDULE
    assert thermostat_listener.attribute_updates[8][1] == 1
    assert thermostat_listener.attribute_updates[9][0] == 0x4002
    assert thermostat_listener.attribute_updates[9][1] == 0
    assert thermostat_listener.attribute_updates[10][0] == 0x001C  # HEAT ON
    assert thermostat_listener.attribute_updates[10][1] == 4


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.ZonnsmartTV01_ZG,))
async def test_zonnsmart_send_attribute(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x10\x02\x00\x04\x00\x00\x00\xfa",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 1,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x02\x04\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 4,  # frost protection wrapped as operation_preset
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x0a\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0,  # SystemMode.Off
            }
        )
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x6b\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.SiterwellGS361_Type1,))
async def test_valve_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)

    frames = (
        ZCL_TUYA_VALVE_TEMPERATURE,
        ZCL_TUYA_VALVE_TARGET_TEMP,
        ZCL_TUYA_VALVE_OFF,
        ZCL_TUYA_VALVE_SCHEDULE,
        ZCL_TUYA_VALVE_MANUAL,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 13
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 500
    assert thermostat_listener.attribute_updates[2][0] == 0x001C  # OFF
    assert thermostat_listener.attribute_updates[2][1] == 0x00
    assert thermostat_listener.attribute_updates[3][0] == 0x001E
    assert thermostat_listener.attribute_updates[3][1] == 0x00
    assert thermostat_listener.attribute_updates[4][0] == 0x0029
    assert thermostat_listener.attribute_updates[4][1] == 0x00
    assert thermostat_listener.attribute_updates[5][0] == 0x001C  # SCHEDULE
    assert thermostat_listener.attribute_updates[5][1] == 0x04
    assert thermostat_listener.attribute_updates[6][0] == 0x0025
    assert thermostat_listener.attribute_updates[6][1] == 0x01
    assert thermostat_listener.attribute_updates[7][0] == 0x001E
    assert thermostat_listener.attribute_updates[7][1] == 0x04
    assert thermostat_listener.attribute_updates[8][0] == 0x0029
    assert thermostat_listener.attribute_updates[8][1] == 0x01
    assert thermostat_listener.attribute_updates[9][0] == 0x001C  # MANUAL
    assert thermostat_listener.attribute_updates[9][1] == 0x04
    assert thermostat_listener.attribute_updates[10][0] == 0x0025
    assert thermostat_listener.attribute_updates[10][1] == 0x00
    assert thermostat_listener.attribute_updates[11][0] == 0x001E
    assert thermostat_listener.attribute_updates[11][1] == 0x04
    assert thermostat_listener.attribute_updates[12][0] == 0x0029
    assert thermostat_listener.attribute_updates[12][1] == 0x01


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.SiterwellGS361_Type1,))
async def test_valve_send_attribute(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x04\x04\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x04\x04\x00\x01\x02",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x01,
            }
        )
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x04\x04\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VALVE_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            61184,
            5,
            b"\x01\x05\x00\x00\x05\x02\x02\x00\x04\x00\x00\x00F",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_trv.MoesHY368_Type1,))
async def test_moes(zigpy_device_from_quirk, quirk):
    """Test thermostatic valve outgoing commands."""

    valve_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = valve_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = valve_dev.endpoints[1].thermostat
    onoff_cluster = valve_dev.endpoints[1].on_off
    thermostat_ui_cluster = valve_dev.endpoints[1].thermostat_ui

    thermostat_listener = ClusterListener(valve_dev.endpoints[1].thermostat)
    onoff_listener = ClusterListener(valve_dev.endpoints[1].on_off)

    frames = (
        ZCL_TUYA_VALVE_TEMPERATURE,
        ZCL_TUYA_VALVE_WINDOW_DETECTION,
        ZCL_TUYA_VALVE_WORKDAY_SCHEDULE,
        ZCL_TUYA_VALVE_WEEKEND_SCHEDULE,
        ZCL_TUYA_VALVE_OFF,
        ZCL_TUYA_VALVE_SCHEDULE,
        ZCL_TUYA_VALVE_MANUAL,
        ZCL_TUYA_VALVE_COMFORT,
        ZCL_TUYA_VALVE_ECO,
        ZCL_TUYA_VALVE_BOOST,
        ZCL_TUYA_VALVE_COMPLEX,
        ZCL_TUYA_VALVE_STATE_50,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 61
    assert thermostat_listener.attribute_updates[0][0] == 0x0000
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x4110
    assert thermostat_listener.attribute_updates[1][1] == 6
    assert thermostat_listener.attribute_updates[2][0] == 0x4111
    assert thermostat_listener.attribute_updates[2][1] == 0
    assert thermostat_listener.attribute_updates[3][0] == 0x4112
    assert thermostat_listener.attribute_updates[3][1] == 2000
    assert thermostat_listener.attribute_updates[4][0] == 0x4120
    assert thermostat_listener.attribute_updates[4][1] == 8
    assert thermostat_listener.attribute_updates[5][0] == 0x4121
    assert thermostat_listener.attribute_updates[5][1] == 0
    assert thermostat_listener.attribute_updates[6][0] == 0x4122
    assert thermostat_listener.attribute_updates[6][1] == 1500
    assert thermostat_listener.attribute_updates[7][0] == 0x4130
    assert thermostat_listener.attribute_updates[7][1] == 11
    assert thermostat_listener.attribute_updates[8][0] == 0x4131
    assert thermostat_listener.attribute_updates[8][1] == 30
    assert thermostat_listener.attribute_updates[9][0] == 0x4132
    assert thermostat_listener.attribute_updates[9][1] == 1500
    assert thermostat_listener.attribute_updates[10][0] == 0x4140
    assert thermostat_listener.attribute_updates[10][1] == 12
    assert thermostat_listener.attribute_updates[11][0] == 0x4141
    assert thermostat_listener.attribute_updates[11][1] == 30
    assert thermostat_listener.attribute_updates[12][0] == 0x4142
    assert thermostat_listener.attribute_updates[12][1] == 1500
    assert thermostat_listener.attribute_updates[13][0] == 0x4150
    assert thermostat_listener.attribute_updates[13][1] == 17
    assert thermostat_listener.attribute_updates[14][0] == 0x4151
    assert thermostat_listener.attribute_updates[14][1] == 30
    assert thermostat_listener.attribute_updates[15][0] == 0x4152
    assert thermostat_listener.attribute_updates[15][1] == 2000
    assert thermostat_listener.attribute_updates[16][0] == 0x4160
    assert thermostat_listener.attribute_updates[16][1] == 22
    assert thermostat_listener.attribute_updates[17][0] == 0x4161
    assert thermostat_listener.attribute_updates[17][1] == 0
    assert thermostat_listener.attribute_updates[18][0] == 0x4162
    assert thermostat_listener.attribute_updates[18][1] == 1500
    assert thermostat_listener.attribute_updates[19][0] == 0x4210
    assert thermostat_listener.attribute_updates[19][1] == 6
    assert thermostat_listener.attribute_updates[20][0] == 0x4211
    assert thermostat_listener.attribute_updates[20][1] == 0
    assert thermostat_listener.attribute_updates[21][0] == 0x4212
    assert thermostat_listener.attribute_updates[21][1] == 2000
    assert thermostat_listener.attribute_updates[22][0] == 0x4220
    assert thermostat_listener.attribute_updates[22][1] == 8
    assert thermostat_listener.attribute_updates[23][0] == 0x4221
    assert thermostat_listener.attribute_updates[23][1] == 0
    assert thermostat_listener.attribute_updates[24][0] == 0x4222
    assert thermostat_listener.attribute_updates[24][1] == 1500
    assert thermostat_listener.attribute_updates[25][0] == 0x4230
    assert thermostat_listener.attribute_updates[25][1] == 11
    assert thermostat_listener.attribute_updates[26][0] == 0x4231
    assert thermostat_listener.attribute_updates[26][1] == 30
    assert thermostat_listener.attribute_updates[27][0] == 0x4232
    assert thermostat_listener.attribute_updates[27][1] == 1500
    assert thermostat_listener.attribute_updates[28][0] == 0x4240
    assert thermostat_listener.attribute_updates[28][1] == 12
    assert thermostat_listener.attribute_updates[29][0] == 0x4241
    assert thermostat_listener.attribute_updates[29][1] == 30
    assert thermostat_listener.attribute_updates[30][0] == 0x4242
    assert thermostat_listener.attribute_updates[30][1] == 1500
    assert thermostat_listener.attribute_updates[31][0] == 0x4250
    assert thermostat_listener.attribute_updates[31][1] == 17
    assert thermostat_listener.attribute_updates[32][0] == 0x4251
    assert thermostat_listener.attribute_updates[32][1] == 30
    assert thermostat_listener.attribute_updates[33][0] == 0x4252
    assert thermostat_listener.attribute_updates[33][1] == 2000
    assert thermostat_listener.attribute_updates[34][0] == 0x4260
    assert thermostat_listener.attribute_updates[34][1] == 22
    assert thermostat_listener.attribute_updates[35][0] == 0x4261
    assert thermostat_listener.attribute_updates[35][1] == 0
    assert thermostat_listener.attribute_updates[36][0] == 0x4262
    assert thermostat_listener.attribute_updates[36][1] == 1500
    assert thermostat_listener.attribute_updates[37][0] == 0x4002
    assert thermostat_listener.attribute_updates[37][1] == 0
    assert thermostat_listener.attribute_updates[38][0] == 0x0025
    assert thermostat_listener.attribute_updates[38][1] == 0
    assert thermostat_listener.attribute_updates[39][0] == 0x0002
    assert thermostat_listener.attribute_updates[39][1] == 0
    assert thermostat_listener.attribute_updates[40][0] == 0x4002
    assert thermostat_listener.attribute_updates[40][1] == 1
    assert thermostat_listener.attribute_updates[41][0] == 0x0025
    assert thermostat_listener.attribute_updates[41][1] == 1
    assert thermostat_listener.attribute_updates[42][0] == 0x0002
    assert thermostat_listener.attribute_updates[42][1] == 1
    assert thermostat_listener.attribute_updates[43][0] == 0x4002
    assert thermostat_listener.attribute_updates[43][1] == 2
    assert thermostat_listener.attribute_updates[44][0] == 0x0025
    assert thermostat_listener.attribute_updates[44][1] == 0
    assert thermostat_listener.attribute_updates[45][0] == 0x0002
    assert thermostat_listener.attribute_updates[45][1] == 1
    assert thermostat_listener.attribute_updates[46][0] == 0x4002
    assert thermostat_listener.attribute_updates[46][1] == 3
    assert thermostat_listener.attribute_updates[47][0] == 0x0025
    assert thermostat_listener.attribute_updates[47][1] == 0
    assert thermostat_listener.attribute_updates[48][0] == 0x0002
    assert thermostat_listener.attribute_updates[48][1] == 1
    assert thermostat_listener.attribute_updates[49][0] == 0x4002
    assert thermostat_listener.attribute_updates[49][1] == 4
    assert thermostat_listener.attribute_updates[50][0] == 0x0025
    assert thermostat_listener.attribute_updates[50][1] == 4
    assert thermostat_listener.attribute_updates[51][0] == 0x0002
    assert thermostat_listener.attribute_updates[51][1] == 1
    assert thermostat_listener.attribute_updates[52][0] == 0x4002
    assert thermostat_listener.attribute_updates[52][1] == 5
    assert thermostat_listener.attribute_updates[53][0] == 0x0025
    assert thermostat_listener.attribute_updates[53][1] == 0
    assert thermostat_listener.attribute_updates[54][0] == 0x0002
    assert thermostat_listener.attribute_updates[54][1] == 1
    assert thermostat_listener.attribute_updates[55][0] == 0x4002
    assert thermostat_listener.attribute_updates[55][1] == 6
    assert thermostat_listener.attribute_updates[56][0] == 0x0025
    assert thermostat_listener.attribute_updates[56][1] == 0
    assert thermostat_listener.attribute_updates[57][0] == 0x0002
    assert thermostat_listener.attribute_updates[57][1] == 1
    assert thermostat_listener.attribute_updates[58][0] == 0x4004
    assert thermostat_listener.attribute_updates[58][1] == 50
    assert thermostat_listener.attribute_updates[59][0] == 0x001E
    assert thermostat_listener.attribute_updates[59][1] == 4
    assert thermostat_listener.attribute_updates[60][0] == 0x0029
    assert thermostat_listener.attribute_updates[60][1] == 1

    assert len(onoff_listener.cluster_commands) == 0
    assert len(onoff_listener.attribute_updates) == 3
    assert onoff_listener.attribute_updates[0][0] == 0x6001
    assert onoff_listener.attribute_updates[0][1] == 5
    assert onoff_listener.attribute_updates[1][0] == 0x6000
    assert onoff_listener.attribute_updates[1][1] == 1600
    assert onoff_listener.attribute_updates[2][0] == 0x0000  # TARGET
    assert onoff_listener.attribute_updates[2][1] == 1

    thermostat_ui_listener = ClusterListener(valve_dev.endpoints[1].thermostat_ui)
    power_listener = ClusterListener(valve_dev.endpoints[1].power)

    frames = (
        ZCL_TUYA_VALVE_CHILD_LOCK_ON,
        ZCL_TUYA_VALVE_AUTO_LOCK_ON,
        ZCL_TUYA_VALVE_BATTERY_LOW,
    )
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_ui_listener.cluster_commands) == 0
    assert len(thermostat_ui_listener.attribute_updates) == 2
    assert thermostat_ui_listener.attribute_updates[0][0] == 0x0001
    assert thermostat_ui_listener.attribute_updates[0][1] == 1
    assert thermostat_ui_listener.attribute_updates[1][0] == 0x5000
    assert thermostat_ui_listener.attribute_updates[1][1] == 1

    assert len(power_listener.cluster_commands) == 0
    assert len(power_listener.attribute_updates) == 1
    assert power_listener.attribute_updates[0][0] == 0x0021
    assert power_listener.attribute_updates[0][1] == 10

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x02\x02\x00\x04\x00\x00\x00\xfa",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x04\x04\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "operation_preset": 0x02,
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x04\x04\x00\x01\x02",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_VALVE_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x02\x02\x00\x04\x00\x00\x00F",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        (status,) = await onoff_cluster.write_attributes(
            {
                "on_off": 0x00,
                "window_detection_timeout_minutes": 0x02,
                "window_detection_temperature": 2000,
            }
        )
        m1.assert_called_with(
            61184,
            5,
            b"\x01\x05\x00\x00\x05\x68\x00\x00\x03\x00\x14\x02",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupancy": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            6,
            b"\x01\x06\x00\x00\x06\x04\x04\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupancy": 0x01,
                "programing_oper_mode": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            7,
            b"\x01\x07\x00\x00\x07\x04\x04\x00\x01\x02",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x01,
            }
        )
        m1.assert_called_with(
            61184,
            8,
            b"\x01\x08\x00\x00\x08\x04\x04\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "programing_oper_mode": 0x04,
            }
        )
        m1.assert_called_with(
            61184,
            9,
            b"\x01\x09\x00\x00\x09\x04\x04\x00\x01\x04",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_temperature": 1700,
            }
        )
        m1.assert_called_with(
            61184,
            10,
            b"\x01\x0A\x00\x00\x0A\x70\x00\x00\x12\x06\x00\x11\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_minute": 45,
            }
        )
        m1.assert_called_with(
            61184,
            11,
            b"\x01\x0B\x00\x00\x0B\x70\x00\x00\x12\x06\x2D\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "workday_schedule_1_hour": 5,
            }
        )
        m1.assert_called_with(
            61184,
            12,
            b"\x01\x0C\x00\x00\x0C\x70\x00\x00\x12\x05\x00\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_temperature": 1700,
            }
        )
        m1.assert_called_with(
            61184,
            13,
            b"\x01\x0D\x00\x00\x0D\x71\x00\x00\x12\x06\x00\x11\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_minute": 45,
            }
        )
        m1.assert_called_with(
            61184,
            14,
            b"\x01\x0E\x00\x00\x0E\x71\x00\x00\x12\x06\x2D\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "weekend_schedule_1_hour": 5,
            }
        )
        m1.assert_called_with(
            61184,
            15,
            b"\x01\x0F\x00\x00\x0F\x71\x00\x00\x12\x05\x00\x14\x08\x00\x0F\x0B\x1E\x0F\x0C\x1E\x0F\x11\x1E\x14\x16\x00\x0F",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x01,
            }
        )
        m1.assert_called_with(
            61184,
            16,
            b"\x01\x10\x00\x00\x10\x04\x04\x00\x01\x06",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_ui_cluster.write_attributes(
            {
                "auto_lock": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            17,
            b"\x01\x11\x00\x00\x11\x74\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        _, status = await onoff_cluster.command(0x0000)
        m1.assert_called_with(
            61184,
            18,
            b"\x01\x12\x00\x00\x12\x68\x00\x00\x03\x00\x10\x05",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await onoff_cluster.command(0x0001)

        m1.assert_called_with(
            61184,
            19,
            b"\x01\x13\x00\x00\x13\x68\x00\x00\x03\x01\x10\x05",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await onoff_cluster.command(0x0002)
        m1.assert_called_with(
            61184,
            20,
            b"\x01\x14\x00\x00\x14\x68\x00\x00\x03\x00\x10\x05",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        (status,) = await onoff_cluster.write_attributes({})
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND

        _, status = await onoff_cluster.command(0x0009)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND

        origdatetime = datetime.datetime
        datetime.datetime = NewDatetime

        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_SET_TIME_REQUEST)
        tuya_cluster.handle_message(hdr, args)
        m1.assert_called_with(
            61184,
            21,
            b"\x01\x15\x24\x00\x08\x00\x00\x1C\x20\x00\x00\x0E\x10",
            expect_reply=False,
            command_id=0x0024,
        )
        datetime.datetime = origdatetime


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_electric_heating.MoesBHT,))
async def test_eheating_state_report(zigpy_device_from_quirk, quirk):
    """Test thermostatic valves standard reporting from incoming commands."""

    electric_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = electric_dev.endpoints[1].tuya_manufacturer

    thermostat_listener = ClusterListener(electric_dev.endpoints[1].thermostat)

    frames = (ZCL_TUYA_EHEAT_TEMPERATURE, ZCL_TUYA_EHEAT_TARGET_TEMP)
    for frame in frames:
        hdr, args = tuya_cluster.deserialize(frame)
        tuya_cluster.handle_message(hdr, args)

    assert len(thermostat_listener.cluster_commands) == 0
    assert len(thermostat_listener.attribute_updates) == 2
    assert thermostat_listener.attribute_updates[0][0] == 0x0000  # TEMP
    assert thermostat_listener.attribute_updates[0][1] == 1790
    assert thermostat_listener.attribute_updates[1][0] == 0x0012  # TARGET
    assert thermostat_listener.attribute_updates[1][1] == 2100


@pytest.mark.parametrize("quirk", (zhaquirks.tuya.ts0601_electric_heating.MoesBHT,))
async def test_eheat_send_attribute(zigpy_device_from_quirk, quirk):
    """Test electric thermostat outgoing commands."""

    eheat_dev = zigpy_device_from_quirk(quirk)
    tuya_cluster = eheat_dev.endpoints[1].tuya_manufacturer
    thermostat_cluster = eheat_dev.endpoints[1].thermostat

    async def async_success(*args, **kwargs):
        return foundation.Status.SUCCESS

    with mock.patch.object(
        tuya_cluster.endpoint, "request", side_effect=async_success
    ) as m1:

        (status,) = await thermostat_cluster.write_attributes(
            {
                "occupied_heating_setpoint": 2500,
            }
        )
        m1.assert_called_with(
            61184,
            1,
            b"\x01\x01\x00\x00\x01\x10\x02\x00\x04\x00\x00\x00\x19",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x00,
            }
        )
        m1.assert_called_with(
            61184,
            2,
            b"\x01\x02\x00\x00\x02\x01\x01\x00\x01\x00",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        (status,) = await thermostat_cluster.write_attributes(
            {
                "system_mode": 0x04,
            }
        )
        m1.assert_called_with(
            61184,
            3,
            b"\x01\x03\x00\x00\x03\x01\x01\x00\x01\x01",
            expect_reply=False,
            command_id=0,
        )
        assert status == [
            foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)
        ]

        # simulate a target temp update so that relative changes can work
        hdr, args = tuya_cluster.deserialize(ZCL_TUYA_EHEAT_TARGET_TEMP)
        tuya_cluster.handle_message(hdr, args)
        _, status = await thermostat_cluster.command(0x0000, 0x00, 20)
        m1.assert_called_with(
            61184,
            4,
            b"\x01\x04\x00\x00\x04\x10\x02\x00\x04\x00\x00\x00\x17",
            expect_reply=False,
            command_id=0,
        )
        assert status == foundation.Status.SUCCESS

        _, status = await thermostat_cluster.command(0x0002)
        assert status == foundation.Status.UNSUP_CLUSTER_COMMAND


@pytest.mark.parametrize(
    "quirk, manufacturer",
    (
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_TZ3000_awgcnkrh"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_TZ3400_deyjhapk"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_TZ3000_pwgcnkrh"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_TZ3400_leyjhapk"),
        (zhaquirks.tuya.ts0041.TuyaSmartRemote0041TO, "_some_random_manuf"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_TZ3000_owgcnkrh"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "_TZ3000_adkvzooy"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "_TZ3400_keyjhapk"),
        (zhaquirks.tuya.ts0042.TuyaSmartRemote0042TO, "another random manufacturer"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "_TZ3000_bi6lpsew"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "_TZ3000_a7ouggvs"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TI, "another random manufacturer"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "_TZ3000_qzjcsmar"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "_TZ3000_qzjcsmhd"),
        (zhaquirks.tuya.ts0043.TuyaSmartRemote0043TO, "another random manufacturer"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_TZ3000_hjgcnkgs"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_TZ3000_ojgcnkkl"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TI, "_some_random_manuf"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_TZ3400_cdyjhasw"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_TZ3400_pdyjhapl"),
        (zhaquirks.tuya.ts0044.TuyaSmartRemote0044TO, "_some_random_manuf"),
    ),
)
async def test_tuya_wildcard_manufacturer(zigpy_device_from_quirk, quirk, manufacturer):
    """Test thermostatic valve outgoing commands."""

    zigpy_dev = zigpy_device_from_quirk(quirk, apply_quirk=False)
    zigpy_dev.manufacturer = manufacturer

    quirked_dev = get_device(zigpy_dev)
    assert isinstance(quirked_dev, quirk)
