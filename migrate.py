# migrate.py — Run this once on Render
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Add the missing column
    conn.execute(text("""
        ALTER TABLE recommendation 
        ADD COLUMN IF NOT EXISTS sub_category_id INTEGER;
    """))
    
    # Also add the foreign key constraint (optional but clean)
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_recommendation_sub_category'
            ) THEN
                ALTER TABLE recommendation 
                ADD CONSTRAINT fk_recommendation_sub_category 
                FOREIGN KEY (sub_category_id) REFERENCES sub_category(id);
            END IF;
        END $$;
    """))
    
    conn.commit()
    print("✅ Fixed: Added sub_category_id column to recommendation table")
