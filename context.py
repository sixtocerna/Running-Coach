import json
from typing import Tuple
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from connections import DatabaseAPI
from utils import setup_logger, speed_to_pace
from models import WorkoutData


logger = setup_logger('api_logs.log')


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

def generate_workouts_report(workout_id:int) -> str:

    db = DatabaseAPI('db.sqlite3', logger=logger)

    db.get_recent_workouts_data()

def generate_indiviual_workout_report(workout_data:WorkoutData, feedback_data:dict,detailed:bool=False, add_days_since:bool=False) -> str:

    msg = feedback_data.get('feedback')
    rpe = feedback_data.get('rpe')

    if add_days_since:
        today = datetime.now(UTC).date()
        days_since_workout = (today - workout_data.starts.date()).days
        output = f'It has been {days_since_workout} days since this workout. '
    else:
        output=''

    if detailed:
        # Called request and process the file
        laps = workout_data.laps
        output = '\n'

        for num, lap in enumerate(laps):
            lap_as_str = f'Lap #{num+1}'.center(30, '-') +'\n ' + '\n '.join([f'- {name} : {value}' for name,value in lap.items()])
            output+=lap_as_str + '\n'

        if msg:
            output+=f'\nHere is the feedback given "{msg}". '
        if rpe:
            output+=f'The RPE was {rpe}/10.'

        return output

    else:
        # Just get the info from workout data
        summary = workout_data.workout_summary
        avg_speed = float(summary["speed_avg"]) # in min/km
        pace = speed_to_pace(avg_speed)
        output += f'The run consisted of {float(summary['distance_accum'])/1000:0.02f}km in {workout_data.minutes}min (average pace of {pace}). '
        if msg:
            output+=f'Here is the feedback given "{msg}". '
        if rpe:
            output+=f'The RPE was {rpe}/10.'

        return output
    
db = DatabaseAPI('db.sqlite3', logger=logger)
most_recent_workout = db.get_recent_workouts_data(1)[0]
id_ = most_recent_workout.id

feedback = db.get_feedback_from_workouts([id_])[0]

print(generate_indiviual_workout_report(most_recent_workout, feedback_data=feedback, detailed=True, add_days_since=True))
