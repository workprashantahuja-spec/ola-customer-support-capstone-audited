# Task 3: two working policy-search indexes

Track: **Ola — Business Operations / Customer Support**.

Task 3 is implemented and tested with the 12 fictional policy documents from Task 2. It converts their chunks into real local SentenceTransformers embeddings, writes them to two separate persistent ChromaDB collections using `collection.upsert()`, and retrieves source passages from either collection.

This task returns passages and their sources. Generated answers, the calibrated out-of-scope fallback, and precision/recall evaluation belong to Tasks 4 and 5 and are still pending.

## What was built

| Setting | Fixed-size strategy | Sentence-based strategy |
| --- | --- | --- |
| Collection | `ola_fixed_v1` | `ola_sentence_v1` |
| Splitting rule | 400-character body windows, 80-character overlap | Two complete sentences per group, no overlap |
| Final short chunk | Retained | Retained |
| Policy documents | 12 | 12 |
| Stored chunks | 31 | 36 |
| Embedding dimensions | 384 | 384 |
| Distance | Cosine distance | Cosine distance |
| Longest embedded chunk in this run | 93 tokens | 80 tokens |

Both strategies prepend the policy title to each chunk before embedding and use the same model and normalized embeddings. The 400-character limit applies to the body window, excluding this shared title prefix. The same model embeds questions and policy chunks. No chunks exceeded the model's configured token limit.

Model: `sentence-transformers/all-MiniLM-L6-v2`.

Pinned model revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Every chunk stores its parent document ID, title, source filename, strategy, position, character offsets, and source-file hash. Offsets refer to the policy body after whitespace normalization. These parent IDs let us deduplicate source documents during the later precision/recall evaluation.

The sentence splitter is intentionally scoped to our authored policies, which do not contain ambiguous abbreviated sentence endings or decimal punctuation. Revisit the splitter before adding documents with those forms.

## Files and their roles

| File | Purpose |
| --- | --- |
| `rag_config.py` | Model identity, pinned revision, paths, chunk settings, and collection names. |
| `prepare_model.py` | One-time model download; requires internet during setup. |
| `rag_index.py` | Load policies, split them, embed them, build both indexes, and search either one. |
| `requirements.txt` | Pin the main tested dependencies. |
| `verify_task3.py` | Reproduce the build, repeated-upsert, sample-search, and separate-process reopening checks. |
| `tests/test_chunking.py` | Four focused checks for coverage, overlap, sentence boundaries, IDs, and source offsets. |
| `transcripts/task3_search_check.json` | Actual integration results, version information, source passages, and similarities. |
| `transcripts/task3_chunking_check.txt` | The executed chunking-test output. |

The downloadable starter contains code, policy text, instructions, and execution evidence. Model weights, installed packages, and generated Chroma files are setup/runtime files: recreate them using the commands below instead of adding them to the final GitHub submission.

## Windows setup in VS Code

No register is needed. Extract the updated archive into your `capstone-project` folder, keeping the files and subfolders together. Open that folder using **VS Code → File → Open Folder**, then open **Terminal → New Terminal** with PowerShell selected.

The following commands assume your existing Python installation is on PATH. These instructions use the environment's Python executable directly, so activation and PowerShell execution-policy changes are unnecessary.

1. Create the project environment if it does not already exist:

```powershell
python -m venv .venv
```

2. Install CPU PyTorch first, then the project requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Download the pinned embedding model once:

```powershell
.\.venv\Scripts\python.exe prepare_model.py
```

This setup command checks that the downloaded SafeTensors weights are readable. If a download was interrupted, it downloads the model files again instead of leaving a corrupt local model that fails later.

4. Build both collections:

```powershell
.\.venv\Scripts\python.exe rag_index.py build
```

Expected collection counts: **31 fixed-size chunks** and **36 sentence-based chunks**, each with **384 dimensions**. Chroma stores them locally under `storage/chroma/`.

5. Ask the same question of both indexes:

```powershell
.\.venv\Scripts\python.exe rag_index.py query "What is the maximum service credit for one incident?" --strategy fixed
.\.venv\Scripts\python.exe rag_index.py query "What is the maximum service credit for one incident?" --strategy sentence
```

The returned hits identify `08_service_credits.md` and include its policy text. A hit's cosine similarity is a retrieval score, not a probability that an answer is correct.

6. Reproduce the checks when needed:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe verify_task3.py
```

For Linux/macOS, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

## Actual verification results

The integration run used Linux and Python 3.12.13, with PyTorch 2.14.0+cpu, SentenceTransformers 6.0.1, ChromaDB 1.5.9, Transformers 5.16.1, Hugging Face Hub 1.30.0, and NumPy 2.5.2. Windows commands are supplied, but have not been executed on Prashant's laptop.

| Test question | First source in both collections | Fixed top similarity | Sentence top similarity |
| --- | --- | ---: | ---: |
| What is the maximum service credit for one incident? | `08_service_credits.md` | 0.568735 | 0.531457 |
| How long are request logs retained? | `12_ticket_data_retention.md` | 0.579142 | 0.595885 |
| Is routine support available on Sunday? | `06_business_hours_and_holidays.md` | 0.624197 | 0.638851 |

- All six searches included the intended document in their first three results; inspection also confirmed it was the first result in every case.
- Repeated builds kept the collection counts at 31 and 36, showing that upsert does not duplicate the indexed chunks.
- A separate Python process reopened both persistent collections and retrieved the service-credit policy without rebuilding.
- The four chunking tests passed.
- Python socket connections and DNS calls were blocked during the integration build and queries. This is a Python-level network check, not an operating-system network-isolation test.

These three sample questions establish that Task 3 retrieval works. They do not establish overall accuracy, choose a winning chunking strategy, or replace the formal evaluations required later. Small numerical differences can occur across hardware and package builds.

## Offline behavior and maintenance

Only package installation and `prepare_model.py` need internet. `rag_index.py` loads the saved model using `local_files_only=True`, sets offline flags before importing the model library, disables Chroma telemetry, and supplies explicit embeddings rather than asking Chroma to download an embedding model. Neither indexing nor retrieval calls a paid language model or needs an API key.

Run `rag_index.py build` again after editing, adding, or removing a policy document. It updates current chunk IDs and removes stale IDs from the two project collections. The query path checks a knowledge-base fingerprint to reject searches against outdated policy content. Changes to the embedding model or chunk configuration require a fresh project index with matching settings.

## Official implementation references

- [SentenceTransformers model loading and encoding](https://sbert.net/docs/package_reference/sentence_transformer/model.html): loading local model files and generating embeddings.
- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2): the selected public embedding model.
- [Chroma collection configuration](https://docs.trychroma.com/docs/collections/configure): selecting cosine distance for the collections.
- [Chroma upsert](https://docs.trychroma.com/docs/collections/update-data): inserting new records and updating existing IDs.
- [Chroma queries](https://docs.trychroma.com/docs/querying-collections/query-and-get): retrieving records using query embeddings.
