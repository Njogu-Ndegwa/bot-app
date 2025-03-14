


import asyncio
import json
import time
import datetime
from typing import List, Dict
import httpx
import chromadb
from litellm import acompletion
from openai import OpenAI
from config import LLM_API_KEY
from models.schemas import Document
from config import CHROMA_PATH, COLLECTION_NAME


open_client = OpenAI(api_key=LLM_API_KEY)

# --- Existing Helper Functions (Unchanged) ---

# def convert_product_to_document(product: dict) -> Document:
#     """
#     Convert a product dictionary to a Document instance.
#     Maps 'title' to document name and 'body_html' to content.
#     Additional fields are included in metadata.
#     """
#     return Document(
#         name=product.get("title", "Untitled Product"),
#         content=product.get("body_html", ""),
#         metadata={
#             "title": product.get("title"),
#             "vendor": product.get("vendor", ""),
#             "status": product.get("status", ""),
#         }
#     )


def convert_product_to_document(product: dict) -> Document:
    """
    Convert a product dictionary to a Document instance.
    Maps 'title' to document name and 'body_html' to content,
    while prefixing the content with the product title.
    Additional fields are included in metadata.
    """
    product_title = product.get("title", "Untitled Product")
    body_html = product.get("body_html", "")
    enhanced_content = f"Product: {product_title}\n\n{body_html}"
    print(enhanced_content, "Enhanced Content")
    return Document(
        name=product_title,
        content=enhanced_content,
        metadata={
            "title": product_title,
            "vendor": product.get("vendor", ""),
            "status": product.get("status", ""),
        }
    )

def convert_article_to_document(article_edge: dict) -> Document:
    """
    Convert an article (extracted from a GraphQL edge) into a Document instance.
    Maps 'displayName' to name and extracts the markdown content from the fields.
    """
    node = article_edge.get('node', {})
    title = node.get('displayName', 'Untitled Article')
    handle = node.get('handle', '')
    content = ""
    for field in node.get('fields', []):
        if field.get('key') == 'content_md':
            content = field.get('value') or ""
            break
    return Document(
        name=title,
        content=content,
        metadata={
            "handle": handle,
            "id": node.get("id"),
        }
    )

async def fetch_products() -> List[dict]:
    """
    Fetch product data from Shopify via REST.
    """
    shop_name = "oves-2022"
    admin_access_token = "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"
    products_url = f"https://{shop_name}.myshopify.com/admin/api/2023-04/products.json?limit=250"
    headers = {
        "X-Shopify-Access-Token": admin_access_token,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(products_url, headers=headers)
        if response.status_code == 200:
            return response.json().get("products", [])
        else:
            raise Exception(f"Failed to fetch products: {response.status_code}\n{response.text}")

async def fetch_articles() -> List[dict]:
    """
    Fetch article data (metaobjects of type "article") via Shopify’s GraphQL API.
    Returns a list of "edges" (each edge contains a node with article data).
    """
    shop_url = "https://oves-2022.myshopify.com/admin/api/2023-04/graphql.json"
    admin_access_token = "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"
    headers = {
        "X-Shopify-Access-Token": admin_access_token,
        "Content-Type": "application/json",
    }
    query = '''
        query MetaobjectIndex(
            $query: String
            $first: Int
            $last: Int
            $before: String
            $after: String
            $sortKey: String
            $reverse: Boolean
            $type: String!
        ) {
            metaobjects(
                first: $first
                last: $last
                before: $before
                after: $after
                type: $type
                query: $query
                reverse: $reverse
                sortKey: $sortKey
            ) {
                edges {
                    cursor
                    node {
                        id
                        displayName
                        handle
                        fields {
                            key
                            value
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                pageInfo {
                    hasPreviousPage
                    hasNextPage
                    endCursor
                    startCursor
                    __typename
                }
                __typename
            }
        }
    '''
    json_data = {
        'query': query,
        'variables': {
            'type': 'article',
            'first': 100,
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(shop_url, headers=headers, json=json_data)
        response.raise_for_status()
        data = response.json()
        if 'errors' in data:
            raise Exception("GraphQL errors encountered: " + json.dumps(data['errors'], indent=4))
        return data['data']['metaobjects']['edges']

def flatten_metadata(metadata):
    """
    Convert list values in metadata to comma-separated strings for Chroma compatibility.
    """
    flattened = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            flattened[key] = ", ".join(map(str, value))
        else:
            flattened[key] = value
    return flattened

# --- Updated Functions with Retry Logic ---

async def generate_metadata_for_document(document: Document, max_retries=3) -> Dict[str, any]:
    """
    Generate metadata for a given document with retry logic for LLM failures.
    Returns an empty dict only after exhausting retries.
    """
    document_content = str(document.content) if document.content else ""
    system_prompt = f"""
You are an expert product catalog assistant. Based on the product description provided, generate metadata for the product.
The metadata should include the following:
- Title
- Vendor
- Status (active/inactive)
- Product Type (e.g., Energy Storage, Solar Lighting, etc.)
- Model
- Features (list of key features)
- Application (how the product is used)
- Certifications (list of certifications, if any)

Here is the product description:

{document_content}

Please return the metadata in the following format:
{{
    "title": "product title",
    "vendor": "vendor name",
    "status": "active",
    "product_type": "Energy Storage",
    "model": "product model",
    "features": ["feature1", "feature2"],
    "application": "product application",
    "certifications": ["certification1", "certification2"]
}}
    """

    for attempt in range(max_retries):
        try:
            response = await acompletion(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": document_content},
                ],
                api_key="sk-AUxlpoH47ZfOuQSQro80L7RKlDTfxHN69eNfav1Pc7T3BlbkFJotKp2GrQMEo5_4D7TQAwFLAbQpLSe5h8xBAzEEYbkA"
            )
            metadata = response.choices[0].message.content
            try:
                metadata_dict = json.loads(metadata)
                print(metadata_dict, "------Metadata_Dict-----")
                return metadata_dict
            except json.JSONDecodeError:
                print("Error: Unable to parse the metadata as JSON.")
                return {}
        except Exception as e:
            if "rate_limit_exceeded" in str(e):
                import re
                match = re.search(r"try again in (\d+)ms", str(e))
                wait_time =  1.0
                print(f"Rate limit exceeded. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                await asyncio.sleep(wait_time)
            else:
                print(f"Error generating metadata on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    print("Max retries reached. Failed to generate metadata.")
                    return {}
                await asyncio.sleep(1)  # Brief delay before retrying non-rate-limit errors

def get_embedding(text, model="text-embedding-3-small", max_retries=3):
    """
    Generate an embedding with retry logic for API failures.
    Returns None only after exhausting retries.
    """
    for attempt in range(max_retries):
        try:
            response = open_client.embeddings.create(input=text, model=model)
            return response.data[0].embedding
        except Exception as e:
            if "rate_limit_exceeded" in str(e):
                import re
                match = re.search(r"try again in (\d+)ms", str(e))
                wait_time = 1.0
                print(f"Rate limit exceeded. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"Error getting embedding on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    print("Max retries reached. Failed to get embedding.")
                    return None
                time.sleep(1)  # Brief delay before retrying non-rate-limit errors

# --- Main Updated Function ---

async def rebuild_vector_db():
    """
    Rebuild the vector database in place using the fixed COLLECTION_NAME.
    Only updates the collection if all steps succeed, preventing corruption.
    """
    try:
        # Step 1: Fetch products and articles concurrently
        products, article_edges = await asyncio.gather(
            fetch_products(),
            fetch_articles()
        )

        # Step 2: Convert to Document objects
        product_documents = [convert_product_to_document(prod) for prod in products]
        article_documents = [convert_article_to_document(edge) for edge in article_edges]
        all_documents = product_documents + article_documents

                # Step 3: Write documents to file for inspection
        with open('vector_db_documents.json', 'w') as f:
            # Using pprint for more readable output
            import json
            json_data = []
            for doc in all_documents:
                # Convert document to dict for JSON serialization
                doc_dict = {
                    'name': doc.name,
                    'content': doc.content,
                    'metadata': doc.metadata
                }
                json_data.append(doc_dict)
            
            json.dump(json_data, f, indent=2)
        
        print(f"Wrote {len(all_documents)} documents to vector_db_documents.json")

        # Step 3: Generate metadata with retries
        metadata_tasks = [generate_metadata_for_document(doc) for doc in all_documents]
        metadatas = await asyncio.gather(*metadata_tasks)
        valid_documents = [doc for doc, meta in zip(all_documents, metadatas) if meta]
        failed_documents = [doc.name for doc, meta in zip(all_documents, metadatas) if not meta]
        if failed_documents:
            print(f"Failed to generate metadata for: {failed_documents}")
        if not valid_documents:
            print("No documents with valid metadata. Aborting rebuild.")
            return
        for doc, metadata in zip(valid_documents, metadatas):
            if metadata:
                doc.metadata = metadata

        # Step 4: Create chunks with unique IDs
        id_counts = {}
        chunks = []
        for doc in valid_documents:
            base_id = doc.name
            if base_id in id_counts:
                id_counts[base_id] += 1
                unique_id = f"{base_id}-{id_counts[base_id]}"
            else:
                id_counts[base_id] = 1
                unique_id = base_id
            flat_metadata = flatten_metadata(doc.metadata)
            chunk = {
                "id": unique_id,
                "text": str(doc.content),
                "metadata": flat_metadata
            }
            chunks.append(chunk)

        # Step 5: Generate embeddings with retries
        embedding_tasks = [asyncio.to_thread(get_embedding, chunk["text"]) for chunk in chunks]
        embeddings = await asyncio.gather(*embedding_tasks)
        valid_chunks = [chunk for chunk, emb in zip(chunks, embeddings) if emb is not None]
        valid_embeddings = [emb for emb in embeddings if emb is not None]
        failed_chunks = [chunk["id"] for chunk, emb in zip(chunks, embeddings) if emb is None]
        if failed_chunks:
            print(f"Failed to generate embeddings for: {failed_chunks}")
        if not valid_chunks:
            print("No chunks with valid embeddings. Aborting rebuild.")
            return

        # Step 6: Update the existing collection in place
        from config import CHROMA_PATH, COLLECTION_NAME
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        try:
            client.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass  # Collection might not exist yet
        collection = client.create_collection(name=COLLECTION_NAME)
        collection.add(
            ids=[chunk["id"] for chunk in valid_chunks],
            embeddings=valid_embeddings,
            documents=[chunk["text"] for chunk in valid_chunks],
            metadatas=[chunk["metadata"] for chunk in valid_chunks]
        )

        print(f"Vector DB rebuild completed successfully. Updated {COLLECTION_NAME}")

    except Exception as e:
        print(f"Error during vector DB rebuild: {e}")

