You are a Senior Staff Software Engineer and AI Systems Architect.

Your goal is NOT to rewrite my code from scratch.

Your goal is to convert my existing Google Colab notebook into a production-grade, modular, scalable AI pipeline that will later be deployed on Google Cloud Platform.

VERY IMPORTANT:

Do NOT change the business logic.

Do NOT optimize prompts.

Do NOT change the algorithms.

Do NOT replace libraries unless absolutely necessary.

Only improve architecture and code organization.

=========================================================
PROJECT CONTEXT
=========================================================

I have a Google Colab notebook that currently performs an end-to-end Etsy asset generation pipeline.

Current pipeline:

Gemini 2.5 Flash 
↓

Prompt Generation (in my current pipeline there is no module need to newly create this module and also we have the skill file for prompt generation that thing we need to use here and model is gemini 2.5 flash)

↓

ComfyUI
(Image Generation)

↓

Background Removal
(rembg)

↓

Image Upscaling

↓

Mockup Generation
(Python)

↓

Gemini 2.5 Flash

↓

Etsy Metadata Generation (In my current pipeline there is no module need to newly create this module and also we have the skill file for metagata generation that thing we need to use here and model is gemini 2.5 flash)

↓

CSV Generation (need to newly create this module)

↓

Etsy Listing Upload (need to newly create this module) 

The notebook currently works.

I want to convert it into a production codebase.

=========================================================
LONG TERM GOAL
=========================================================

This project will eventually run on GCP.

Infrastructure:

Vertex AI
Gemini 2.5 Flash

Compute Engine GPU VM

Cloud Storage

FastAPI

Docker

Later:

Manager Agent

Prompt Agent

Image Agent

Metadata Agent

Quality Agent

SEO Agent

Therefore the architecture MUST be future-proof.

=========================================================
ABSOLUTE REQUIREMENTS
=========================================================

Do NOT build an agent system now.

Do NOT use LangGraph.

Do NOT use CrewAI.

Do NOT use AutoGen.

Do NOT use Vertex AI Agent.

Do NOT introduce unnecessary frameworks.

This version should only prepare the codebase for future agents.

=========================================================
WHAT I WANT
=========================================================

Refactor the notebook into a modular Python package.

Every pipeline stage should become an independent module.

Each module should expose exactly ONE public entry function.

Example:

generate_images(job)

remove_background(job)

upscale(job)

create_mockups(job)

generate_metadata(job)

create_csv(job)

upload_etsy(job)

No stage should directly call another stage.

=========================================================
CREATE A JOB OBJECT
=========================================================

Create a Job model that stores everything shared across the pipeline.

For example:

theme

prompts

generated images

background removed images

upscaled images

mockups

metadata

csv path

logs

status

errors

execution timestamps

This Job object should be passed between modules.

No global variables.

=========================================================
PIPELINE ORCHESTRATOR
=========================================================

Create a Pipeline class.

Pipeline.run(job)

should execute:

Prompt Generation

↓

Image Generation

↓

Background Removal

↓

Upscaling

↓

Mockup

↓

Metadata

↓

CSV

↓

Etsy Upload

The Pipeline should contain zero business logic.

It should only orchestrate.

=========================================================
WORKERS
=========================================================

Every module should internally contain a Worker.

Example

ImageWorker

BackgroundWorker

UpscaleWorker

MockupWorker

MetadataWorker

CSVWorker

EtsyWorker

The Worker contains all implementation.

=========================================================
FUTURE AGENT COMPATIBILITY
=========================================================

Every Worker should later be easily wrapped by an AI Agent.

Example:

class ImageAgent:

    execute(job):

        ImageWorker.run(job)

Do NOT build the agents.

Only make the workers compatible.

=========================================================
DIRECTORY STRUCTURE
=========================================================

Create a professional folder structure.

Example

project/

api/

pipeline/

workers/

models/

services/

config/

utils/

tests/

docker/

scripts/

Do NOT create giant files.

=========================================================
CONFIGURATION
=========================================================

Move every hardcoded value into config.

Examples

API Keys

Paths

GPU settings

Model names

Output folders

Drive locations

Environment variables

=========================================================
LOGGING
=========================================================

Replace print()

with structured logging.

=========================================================
ERROR HANDLING
=========================================================

Every stage should

raise meaningful exceptions

log failures

return proper status

Pipeline should stop safely.

=========================================================
TYPE HINTS
=========================================================

Use full type hints.

=========================================================
DOCSTRINGS
=========================================================

Document every public function.

=========================================================
GOOGLE CLOUD READY
=========================================================

Do NOT use

google.colab

Notebook-only features

Interactive widgets

Cell magic

Shell commands inside Python

Replace notebook-specific code with standard Python.

=========================================================
DOCKER READY
=========================================================

The project should later support

docker compose up

without major changes.

=========================================================
FASTAPI READY
=========================================================

The Pipeline should later be callable like

pipeline.run(job)

inside a FastAPI endpoint.

=========================================================
OUTPUT FORMAT
=========================================================

First:

Explain the proposed architecture.

Second:

Show the complete folder structure.

Third:

Explain every folder.

Fourth:

Explain every module.

Fifth:

Generate the Job model.

Sixth:

Generate the Pipeline class.

Seventh:

Refactor one notebook section at a time.

Never refactor everything at once.

Wait after every stage for review.

=========================================================
IMPORTANT
=========================================================

Do not prioritize writing code.

Prioritize architecture.

The goal is maintainability for the next 5+ years.

Act like a Staff Engineer reviewing a production AI platform.