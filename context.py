import json
from typing import Tuple
from datetime import datetime
from pydantic import BaseModel, Field



class Time(BaseModel):
    hours : int
    minutes: int = Field(..., ge=0, le=60)
    seconds: int = Field(..., ge=0, le=60)

    def __str__(self):

        suffix = ['h', 'min', 's']
        data = [self.hours, self.minutes, self.seconds]

        values = [f'{d}{s}' for s, d in zip(suffix, data) if d>0]

        return ' '.join(values)
    

class RunningParams(BaseModel):

    """Model to manipulate running goals and current progress"""

    time : Time
    distance_m : float

def read_goals_progress_deadline(params_file:str) -> Tuple[RunningParams, RunningParams, datetime]:
    
    with open(params_file, 'r') as f:
        data = f.read()
        data_as_json = json.loads(data)

    goal = RunningParams(**data_as_json['goal'])

    current_progress = RunningParams(**data_as_json['current_progress'])

    deadline = datetime.strptime(data_as_json['deadline'], '%Y-%m-%d')

    return goal, current_progress, deadline


def generate_goal_context():

    goal, current_progress, deadline = read_goals_progress_deadline('params.json')

    days_left = deadline - datetime.today()
    days_left = max(days_left.days, 0)

    output = (
        f'The goal is to run {goal.distance_m:0.0f}m under {goal.time}. The '
        f'current progress is {current_progress.distance_m:0.0f}m in {current_progress.time}. '
        f'Our race is in {days_left} days.' 
    )

    return output

def get_week_context(week_number:int, week_objectives:dict[int, dict]) -> str:

    for stage_num, week_data in week_objectives.items():

        if week_data['start'] <= week_number <= week_data['end']:

            week_ctx = week_objectives[stage_num]

            return (
                f'We are in {week_ctx['title']}. {week_ctx['objective']}'
            )
        
    raise ValueError('Week number out of range')

def read_plan_stucture(filename:str) -> dict:

    with open(filename, 'r') as f:

        data = f.read()
        data = json.loads(data)

    return data
