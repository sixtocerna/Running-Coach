from agents import ExtractWorkoutComponentsAgent, ExtractIntervalsAgent, WorkoutGenerationAgent, SummarizerAgent
from context import generate_user_prompt
from models import get_default_header_data
from models import Plan, Header
import time
import logfire
logfire.configure(scrubbing=False)

time.sleep(3)

def generate_plan()-> Plan:

    user_prompt = generate_user_prompt()

    generated_workout = WorkoutGenerationAgent.run_sync(user_prompt=user_prompt)

    print(generated_workout.data)

    workout_components = ExtractWorkoutComponentsAgent.run_sync(generated_workout.data)

    intervals = ExtractIntervalsAgent.run_sync(str(workout_components.data)).data

    workout_description = SummarizerAgent.run_sync(user_prompt=generated_workout.data).data

    header = Header(**get_default_header_data(name="Today's workout", description=workout_description))

    return Plan(header=header, intervals=intervals)

print(generate_plan())
