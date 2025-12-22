DO \$\$
DECLARE
    cols TEXT[] := ARRAY['daily_poll_sms', 'flash_poll_sms', 'phone_carrier', 'phone_verification_code', 'phone_verification_sent_at', 'phone_verified', 'phone_number', 'sms_notifications'];
    col TEXT;
BEGIN
    FOREACH col IN ARRAY cols
    LOOP
        IF EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = col
        ) THEN
            EXECUTE format('ALTER TABLE users DROP COLUMN IF EXISTS %I', col);
            RAISE NOTICE 'Dropped column: %', col;
        ELSE
            RAISE NOTICE 'Column % does not exist', col;
        END IF;
    END LOOP;
END \$\$;
