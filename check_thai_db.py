import asyncio
from bot.services.vector_db import vector_db
from bot.utils.config import settings

async def check_db():
    vector_db.initialize()
    
    # Ищем все статьи с country='thai'
    results = vector_db.collection.get(
        where={"country": "thai"},
        limit=1000
    )
    
    print(f"Total Thai articles in DB: {len(results['ids'])}")
    
    found_288 = False
    for i, text in enumerate(results['documents']):
        if "Section 288" in text:
            print(f"\nFound Section 288!")
            print(f"ID: {results['ids'][i]}")
            print(f"Metadata: {results['metadatas'][i]}")
            print(f"Text: {text[:200]}...")
            found_288 = True
            break
            
    if not found_288:
        print("\nSection 288 NOT found in DB!")

if __name__ == "__main__":
    asyncio.run(check_db())

