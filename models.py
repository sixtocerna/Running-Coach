from datetime import datetime
from pydantic import BaseModel, field_validator
import requests
from io import BytesIO
import fitparse
from utils import speed_to_pace
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from enum import Enum
import base64
import json

load_dotenv()


class WorkoutData(BaseModel):

    id:int
    starts:datetime
    minutes:int
    name:str
    plan_id:int|None
    route_id:int|None
    workout_token:str
    workout_type_id:int
    day_code:int|None
    workout_summary:dict|None
    created_at:datetime
    updated_at:datetime

    @field_validator('starts', mode='before')
    @classmethod
    def parse_and_convert_to_UTC_starts(cls, value):

        if isinstance(value, str):
            if 'Z' in value:
                value_with_hour_shift = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value_with_hour_shift)
            return datetime.fromisoformat(value)
        
    @field_validator('created_at', mode='before')
    @classmethod
    def parse_and_convert_to_UTC_created_at(cls, value):

        if isinstance(value, str):
            if 'Z' in value:
                value_with_hour_shift = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value_with_hour_shift)
            return datetime.fromisoformat(value)
        
    @field_validator('updated_at', mode='before')
    @classmethod
    def parse_and_convert_to_UTC_updated_at(cls, value):

        if isinstance(value, str):
            if 'Z' in value:
                value_with_hour_shift = value.replace("Z", "+00:00")
                return datetime.fromisoformat(value_with_hour_shift)
            return datetime.fromisoformat(value)
        
    @property
    def _fit_file_url(self) -> str:
        return self.workout_summary['file']['url']
    
    @property
    def laps(self) -> list[dict]:

        response = requests.get(self._fit_file_url)

        response.raise_for_status()

        fitfile = fitparse.FitFile(BytesIO(response.content))

        output = []

        relevant_fields = {
            'avg_speed':'Average speed', 
            'total_distance':'Total distance', 
            'total_elapsed_time':'Total elapsed time',
            'total_descent':'Total descent', 
            'total_ascent':'Total ascent', 
            'avg_grade':'Average grade'
        }

        for lap in fitfile.get_messages('lap'):
            
            lap_data = {}

            for field_key, field_name in relevant_fields.items():

                if field_key == 'avg_speed':
                    value = lap.get_value(field_key)
                    lap_data[field_name] = speed_to_pace(value)
                    
                elif field_key == 'total_elapsed_time':
                    value = lap.get_value(field_key)
                    minutes = int(value//60) # Convert from secs to min and secs
                    secs = int(value % 60)
                    lap_data[field_name] =  f'{minutes}:{secs}min'
                else:
                    value = str(lap.get(field_key))
                    lap_data[field_name] =  value.replace(']','').replace('[', '')

            output.append(lap_data)

        return output

class WorkoutEndpointResponseJSONModel(BaseModel):
    workouts : list[WorkoutData]
    total : int
    page : int
    per_page: int
    order : str
    sort : str

    # Assert that the API still returns workouts in the expected order

    @field_validator('order')
    @classmethod
    def order_is_descending(cls, value):
        if value == 'descending':
            return value
        
    @field_validator('sort')
    @classmethod
    def ordered_by_start(cls, value):
        if value == 'starts':
            return value

    @property 
    def lastest_starts_date_in_page(self):

        return self.workouts[-1].starts
    

class WorkoutComponent(BaseModel):
    name : str
    description : str
    parameters: str|None
    repetitions: int|None
    subsets: list
    

class Header(BaseModel):
    name: str = Field(..., description="Display name for the plan")
    version: str = Field(..., description="The version is still '1.0.0', so write that")
    description: Optional[str] = Field(None, description="Short description of the plan to be displayed to user (5000 characters max)")
    duration_s: Optional[int] = Field(None, description="Length of the plan in seconds (if omitted, calculated based on intervals)")
    distance_m: Optional[int] = Field(None, description="Length of the plan in meters (if omitted, calculated based on intervals)")
    workout_type_family:int  = Field(..., description="All workouts are running, so write 1")
    workout_type_location:int = Field(..., description="All workouts are outdoors, so write 1")
    threshold_speed: Optional[float] = Field(None, description="Athlete’s threshold speed value in meters per second (used for interval targets)")

class TargetType(str, Enum):
    speed = "speed"  # Speed target in meters per second
    threshold_speed = "threshold_speed"  # Percentage of athlete’s threshold speed

class Target(BaseModel):
    type: TargetType = Field(..., description="The type of target for the interval (e.g., rpm, rpe, watts, hr, speed)")
    low: float = Field(..., description="The lowest value for the target to be considered 'in range'")
    high: float = Field(..., description="The highest value for the target to be considered 'in range'")

class TriggerType(str, Enum):
    time = "time"  # Measured in seconds
    distance = "distance"  # Measured in meters
    repeat = "repeat"  # Number of times to repeat the interval (after the first iteration)

class IntensityType(str, Enum):
    active = "active"  
    wu = "warm up"  
    tempo = "tempo"  
    lt = "lactate threshold"  
    map = "maximal aerobic power"  
    ac = "anaerobic capacity"  
    cd = "cool down"  
    recover = "recovery"  
    rest = "rest"  

class Interval(BaseModel):
    name: Optional[str] = Field(default=None, description="Display name for the interval (e.g., Warm-up, Sprint)")
    exit_trigger_type: TriggerType = Field(..., description="Type of trigger to end the interval (e.g., time, distance, repeat)")
    exit_trigger_value: float = Field(..., description="Value for the exit trigger (e.g., duration in seconds, distance in meters, or repetitions)")
    intensity_type: Optional[IntensityType] = Field(default=None, description="Intensity type label for the interval (e.g., warmup, tempo, cooldown)")
    targets: Optional[List[Target]] = Field(default=None, description="List of target values and controls for the interval, valid only if exit_trigger_type is not 'repeat'")
    intervals: Optional[List['Interval']] = Field(default=None, description="Nested intervals used for repetitions when exit_trigger_type is 'repeat'")

    @model_validator(mode='after')
    def validate_targets_and_intervals(self):
        targets = self.targets
        intervals = self.intervals

        if targets:
            if intervals:
                return ValueError('If there are nested intervals, please remove targets in the parent interval.')
        
        if not intervals and not targets:
            return ValueError('Please add the target provided in the plan for the interval.')
        
        return self
    
class Plan(BaseModel):
    
    header : Header 
    intervals : List[Interval]

    def to_payload(self) -> str:

        json_content = {
            'header':self.header.model_dump(),
            'intervals':[i.model_dump() for i in self.intervals]
        }
        json_string = json.dumps(json_content).encode('utf-8')
        base64_bytes = base64.b64encode(json_string)

        return base64_bytes.decode('utf-8')

