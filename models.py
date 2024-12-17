from datetime import datetime
from pydantic import BaseModel, field_validator


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
            value_with_hour_shift = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value_with_hour_shift)
        
    @field_validator('created_at', mode='before')
    @classmethod
    def parse_and_convert_to_UTC_created_at(cls, value):

        if isinstance(value, str):
            value_with_hour_shift = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value_with_hour_shift)
        
    @field_validator('updated_at', mode='before')
    @classmethod
    def parse_and_convert_to_UTC_updated_at(cls, value):

        if isinstance(value, str):
            value_with_hour_shift = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value_with_hour_shift)

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
    