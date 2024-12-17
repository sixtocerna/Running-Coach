import json
from typing import Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging


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


def setup_logger(log_file: str, level=logging.INFO):
    """
    Set up a logger that writes to a file and prints to the console.
    
    :param log_file: File path for the log file
    :param level: Logging level (e.g., logging.INFO, logging.DEBUG)
    :return: Configured logger
    """
    logger = logging.getLogger()  # Use the root logger
    logger.setLevel(level)

    # Check if handlers already exist (to prevent duplicates)
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger



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


