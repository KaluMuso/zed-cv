-- Add marketing_blurb and is_highlighted to tier_config
ALTER TABLE tier_config 
ADD COLUMN marketing_blurb text,
ADD COLUMN is_highlighted boolean DEFAULT false;

-- Create site_faqs table
CREATE TABLE site_faqs (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    question text NOT NULL,
    answer text NOT NULL,
    is_active boolean DEFAULT true,
    sort_order smallint DEFAULT 0,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Enable RLS on site_faqs
ALTER TABLE site_faqs ENABLE ROW LEVEL SECURITY;

-- Allow public read access to active faqs
CREATE POLICY "Public users can view active faqs" 
ON site_faqs FOR SELECT 
USING (is_active = true);

-- Allow superadmins to manage faqs
CREATE POLICY "Superadmins can manage faqs" 
ON site_faqs FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM users 
        WHERE users.id = auth.uid() 
        AND users.role = 'superadmin'
    )
);

-- Seed initial tier marketing data
UPDATE tier_config SET marketing_blurb = '3 matches/month + WhatsApp alerts', is_highlighted = false WHERE tier = 'free';
UPDATE tier_config SET marketing_blurb = '50 matches/month + WhatsApp alerts', is_highlighted = true WHERE tier = 'starter';
UPDATE tier_config SET marketing_blurb = '125 matches/month + Full insights', is_highlighted = false WHERE tier = 'professional';
UPDATE tier_config SET marketing_blurb = 'Unlimited matches + Priority support', is_highlighted = false WHERE tier = 'super_standard';

-- Seed initial faqs based on hardcoded frontend
INSERT INTO site_faqs (question, answer, sort_order, is_active) VALUES
('How do I apply for jobs?', 'When you receive a match digest on WhatsApp, it includes direct links to apply. We also save the job to your dashboard where you can track its status.', 10, true),
('Can I cancel my subscription?', 'Yes, you can downgrade to the Free tier at any time from your billing settings. Your current tier benefits will remain active until the end of your billing cycle.', 20, true),
('Do employers see my phone number?', 'No. Employers only see the contact details you explicitly include in your CV document. We do not share your WhatsApp number with anyone.', 30, true),
('How does the AI matching work?', 'We use semantic search to compare your CV against hundreds of jobs daily. We look at your skills, experience level, and the specific requirements of the role to find high-probability matches.', 40, true);
