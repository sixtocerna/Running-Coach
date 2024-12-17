from datetime import datetime
from pydantic import BaseModel, field_validator
import requests
from io import BytesIO
import fitparse
from utils import speed_to_pace


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
    