-- Run this ONLY if you already created the database without the review_comment column
ALTER TABLE appeals ADD COLUMN IF NOT EXISTS review_comment TEXT DEFAULT NULL AFTER reviewed_by;
