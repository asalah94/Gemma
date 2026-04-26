# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from medgemma import medgemma_get_text_response


def evaluation_prompt(defacto_condition):
    # Returns a detailed prompt for the LLM to evaluate a pre-visit report for a specific condition
    return f"""
Your role is to evaluate the helpfulness of a pre-visit report, which is based on a pre-visit patient interview and existing health records.
The patient was de facto diagnosed condition: "{defacto_condition}" which was not known at the time of the interview.

List the specific elements in the previsit report text that are helpful or necessary for the PCP to diagnose the de facto diagnosed condition: "{defacto_condition}". 

This include pertinet positives or negatives. 
List critical elements that are MISSING from the previsit report text that would have been helpful for the PCP to diagnose the de facto diagnosed condition. 
This include pertinet positives or negatives that were missing from the report. 
(keep in mind that the condition "{defacto_condition}" was not known at the time)

The evaluation output should be in HTML format.

REPORT TEMPLATE START

<h3 class="helpful">Helpful Facts:</h3>

<h3 class="missing">What wasn't covered but would be helpful:</h3>

REPORT TEMPLATE END
"""

def evaluate_report(report, condition):
    """Evaluate the pre-visit report based on the condition using MedGemma LLM."""
    evaluation_text = medgemma_get_text_response([
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": f"{evaluation_prompt(condition)}"
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Here is the report text:\n{report}"
                }
            ]
        },        
    ])

    # Remove any LLM "thinking" blocks (special tokens sometimes present in output)
    evaluation_text = re.sub(r'<unused94>.*?<unused95>', '', evaluation_text, flags=re.DOTALL)

    return evaluation_text
