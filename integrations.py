from dotenv import load_dotenv
import os
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

load_dotenv()

### Don't use fields related to biking or HR (not accurate enough) ###

#ftp: Optional[int] = Field(None, description="Athlete's FTP value in watts (used for interval targets)")
#map: Optional[int] = Field(None, description="Athlete's MAP value in watts (used for interval targets)")
#ac: Optional[int] = Field(None, description="Athlete's AC value in watts (used for interval targets)")
#nm: Optional[int] = Field(None, description="Athlete's NM value in watts (used for interval targets)")
# threshold_hr: Optional[int] = Field(None, description="Athlete's threshold heart rate value in beats per minute (used for interval targets)")
# max_hr: Optional[int] = Field(None, description="Athlete's maximum heart rate value in beats per minute (used for interval targets)")

class Header(BaseModel):
    name: str = Field(..., description="Display name for the plan")
    version: str = Field(..., description="The version is still '1.0.0', so write that")
    description: Optional[str] = Field(None, description="Short description of the plan to be displayed to user (5000 characters max)")
    duration_s: Optional[int] = Field(None, description="Length of the plan in seconds (if omitted, calculated based on intervals)")
    distance_m: Optional[int] = Field(None, description="Length of the plan in meters (if omitted, calculated based on intervals)")
    workout_type_family:int  = Field(..., description="All workouts are running, so write 1")
    workout_type_location:int = Field(..., description="All workouts are outdoors, so write 1")
    threshold_speed: Optional[float] = Field(None, description="Athlete’s threshold speed value in meters per second (used for interval targets)")

### Don't use target type for bike or HR ###

# rpm = "rpm"  # Cadence target in rotations per minute
# rpe = "rpe"  # Relative perceived effort (1-10)
# watts = "watts"  # Raw power target in watts
# hr = "hr"  # Heart rate target in beats per minute
# ftp = "ftp"  # Percentage of athlete’s FTP
# map = "map"  # Percentage of athlete’s MAP
# ac = "ac"  # Percentage of athlete’s AC
# nm = "nm"  # Percentage of athlete’s NM
# threshold_hr = "threshold_hr"  # Percentage of athlete’s threshold HR
# max_hr = "max_hr"  # Percentage of athlete’s max HR

class TargetType(str, Enum):
    speed = "speed"  # Speed target in meters per second
    threshold_speed = "threshold_speed"  # Percentage of athlete’s threshold speed

class Target(BaseModel):
    type: TargetType = Field(..., description="The type of target for the interval (e.g., rpm, rpe, watts, hr, speed)")
    low: float = Field(..., description="The lowest value for the target to be considered 'in range'")
    high: float = Field(..., description="The highest value for the target to be considered 'in range'")

### Don't use kj : not useful for running ###
# kj = "kj"  # Measured in kilojoules (work performed)
class TriggerType(str, Enum):
    time = "time"  # Measured in seconds
    distance = "distance"  # Measured in meters
    repeat = "repeat"  # Number of times to repeat the interval (after the first iteration)


### Don't use unrelated to running IntensityTypes ### 

# nm = "neuromuscular power"  # Neuromuscular power
# ftp = "functional threshold power"  # Functional threshold power

class IntensityType(str, Enum):
    active = "active"  # Default
    wu = "warm up"  # Warm-up
    tempo = "tempo"  # Tempo
    lt = "lactate threshold"  # Lactate threshold
    map = "maximal aerobic power"  # Maximal aerobic power
    ac = "anaerobic capacity"  # Anaerobic capacity
    cd = "cool down"  # Cool-down
    recover = "recovery"  # Recovery
    rest = "rest"  # Rest

class Interval(BaseModel):
    name: Optional[str] = Field(None, description="Display name for the interval (e.g., Warm-up, Sprint)")
    exit_trigger_type: TriggerType = Field(..., description="Type of trigger to end the interval (e.g., time, distance, repeat)")
    exit_trigger_value: float = Field(..., description="Value for the exit trigger (e.g., duration in seconds, distance in meters, or repetitions)")
    intensity_type: Optional[IntensityType] = Field(..., description="Intensity type label for the interval (e.g., warmup, tempo, cooldown)")
    targets: Optional[List[Target]] = Field(None, description="List of target values and controls for the interval, valid only if exit_trigger_type is not 'repeat'")
    intervals: Optional[List['Interval']] = Field(..., description="Nested intervals used for repetitions when exit_trigger_type is 'repeat'")

class Plan(BaseModel):
    header : Header 
    intervals : List[Interval]

