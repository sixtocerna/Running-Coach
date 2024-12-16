import requests
from auth import token_manager
from datetime import datetime, UTC
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
    created_at:str
    updated_at:str

    @field_validator('starts', mode='before')
    @classmethod
    def parse_and_convert_to_UTC(cls, value):

        if isinstance(value, str):

            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.000Z').astimezone(UTC)


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

        print(self.workouts[-1].starts, self.workouts)

        return self.workouts[-1].starts
    


class WahooAPI:

    def __init__(self):
        self.token_manager = token_manager
        self.base_url = 'https://api.wahooligan.com/v1/'
        
    @property
    def headers(self):
        return {'Authorization':f'Bearer {self.token_manager.get_access_token()}'}


    def _get_workouts_page(self, page:int, per_page) -> WorkoutEndpointResponseJSONModel:

        url = self.base_url + 'workouts'

        response = requests.get(
            url = url,
            headers=self.headers,
            params={'page':page, 'per_page':per_page} # Per page high reduces the number of API calls required
        )

        response.raise_for_status()

        return WorkoutEndpointResponseJSONModel(**response.json())
    

    def read_workouts(self, before:datetime|None=None, per_page:int=50) -> list[WorkoutData]:
        # Before date is in UTC

        first_page = self._get_workouts_page(1, per_page=per_page)

        output = [w for w in first_page.workouts]

        total = first_page.total

        if before:
            # Get only workouts before the specified date

            # Prevent error of comparing naive tz (from before) with UTC time (from API)
            assert before.timetz().tzinfo == UTC, 'Before must be a datetime with UTC'

            last_date_in_response = first_page.lastest_starts_date_in_page

            next_page_num = 2

            # Only go to next page if there are more workouts that could be in the next page
            # that means there are still unseen workouts in later pages that could have
            # a date before the selected date
            
            while last_date_in_response <= before and len(output)<total:
                
                next_page = self._get_workouts_page(next_page_num, per_page=per_page)

                last_date_in_response = next_page.lastest_starts_date_in_page

                output.extend(next_page.workouts)

            return [w for w in output if w.starts<=before]

        else:

            # Get all workouts

            next_page_num = 2

            while total > len(output):

                new_page = self._get_workouts_page(next_page_num, per_page=per_page)

                output.extend(new_page.workouts)

                next_page_num +=1

            return output
    

    def update_plan(self):
        ...

    def upload_plan(self):
        ...

    def delete_plan(self):
        ...


    