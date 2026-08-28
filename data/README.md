# Dataset provenance and isolation

PersonaMem-v1 is published under the MIT license. PersonaMem-v2 is published under CC BY 4.0. Record the exact Hugging Face commit in every concrete experiment manifest and retain the required v2 attribution with derived subsets.

Raw benchmark downloads are not committed. Normalized events and private labels are separate because replay and memory-adapter code should receive only event paths. A manifest is orchestration metadata and must not itself be sent to the tested agent.

The repository is for synthetic, isolated research data. Do not connect the harness to production assistants, real user memories, shared tenant accounts, or tools with external side effects.
