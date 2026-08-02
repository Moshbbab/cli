# Real Estate Value Calculator & Buyer Matching App — Production MVP Blueprint

## 1) System Architecture (Practical, Fast-Launch)

**Architecture style:** modular monolith with clean service boundaries.

- **Frontend:** Next.js (App Router), React, Tailwind CSS
- **Backend:** Next.js API routes (Phase 1), optional extraction to Express/Nest in Phase 3
- **Database:** PostgreSQL (Supabase-hosted for speed)
- **Auth:** Clerk (email/password + Google + Apple)
- **Storage:** Supabase Storage (images + generated PDF reports)
- **Maps/Geo:** [MAP PROVIDER]
- **Payments:** Stripe ([PAYMENT PROVIDER])
- **Analytics:** PostHog + GA4
- **Queue/background jobs:** lightweight cron/worker (report generation, alerts)

### Runtime components
1. **Web app** (SSR + client-side interactivity)
2. **API layer** (auth-protected endpoints)
3. **Valuation service** (deterministic logic with explainability)
4. **Buyer matching service** (rule-based scoring)
5. **Reporting service** (PDF generation)
6. **Admin panel** (data moderation + pricing config)

### Why this architecture
- Ships in days, not months.
- Low ops burden (managed DB/auth/storage).
- Clear migration path toward microservices when usage grows.

---

## 2) Database Schema (MVP)

> Note: simplified schema designed for credibility + speed.

### `users`
- `id` (uuid, pk)
- `auth_provider_id` (text, unique)
- `name` (text)
- `email` (text, unique)
- `phone` (text)
- `investment_preference` (text)
- `budget_min` (numeric)
- `budget_max` (numeric)
- `preferred_locations` (jsonb)
- `created_at`, `updated_at`

### `properties`
- `id` (uuid, pk)
- `user_id` (uuid, fk users)
- `property_type` (enum: residential, apartment, villa, land)
- `address` (text)
- `city` (text)
- `neighborhood` (text)
- `postal_code` (text)
- `lat`, `lng` (numeric)
- `land_area_sqft` (numeric)
- `built_area_sqft` (numeric)
- `bedrooms`, `bathrooms`, `parking_spaces` (int)
- `year_built` (int)
- `renovation_status` (text)
- `interior_quality`, `exterior_quality`, `view_quality` (smallint 1-5)
- `floor_number` (int)
- `amenities` (jsonb)
- `condition` (text)
- `occupancy_status` (text)
- `rental_status` (text)
- `nearby_features` (jsonb)
- `created_at`, `updated_at`

### `market_comps`
- `id` (uuid, pk)
- `property_type` (text)
- `city`, `neighborhood`, `postal_code` (text)
- `lat`, `lng` (numeric)
- `sold_price` (numeric)
- `list_price` (numeric)
- `sold_date` (date)
- `days_on_market` (int)
- `built_area_sqft` (numeric)
- `land_area_sqft` (numeric)
- `bedrooms`, `bathrooms` (int)
- `condition_score` (smallint)
- `amenity_score` (smallint)
- `source` (text: [MLS API], [PROPERTY DATA API])

### `valuations`
- `id` (uuid, pk)
- `property_id` (uuid, fk properties)
- `estimated_value` (numeric)
- `low_range` (numeric)
- `high_range` (numeric)
- `confidence_pct` (numeric)
- `method_sales` (numeric)
- `method_income` (numeric)
- `method_cost` (numeric)
- `market_trend_summary` (text)
- `risk_flags` (jsonb)
- `reasoning` (jsonb)
- `created_at`

### `buyer_profiles`
- `id` (uuid, pk)
- `user_id` (uuid, fk users, nullable for external leads)
- `profile_type` (enum: end_user, investor, developer, land_banker, rental_investor)
- `budget_min`, `budget_max` (numeric)
- `preferred_areas` (jsonb)
- `property_types` (jsonb)
- `target_yield` (numeric)
- `risk_tolerance` (enum: low, medium, high)
- `goals` (text)

### `buyer_matches`
- `id` (uuid, pk)
- `property_id` (uuid, fk properties)
- `buyer_profile_id` (uuid, fk buyer_profiles)
- `match_score` (numeric)
- `conversion_likelihood` (numeric)
- `outreach_message` (text)
- `created_at`

### `saved_properties`
- `id` (uuid, pk)
- `user_id` (uuid)
- `property_id` (uuid)
- `created_at`

### `reports`
- `id` (uuid, pk)
- `property_id` (uuid)
- `valuation_id` (uuid)
- `file_url` (text)
- `is_paid` (bool)
- `price_paid` (numeric)
- `created_at`

### `subscriptions`
- `id` (uuid, pk)
- `user_id` (uuid)
- `stripe_customer_id` (text)
- `plan` (text)
- `status` (text)
- `renewal_date` (date)

### `engagement_events`
- `id` (uuid, pk)
- `user_id` (uuid)
- `property_id` (uuid, nullable)
- `event_type` (text)
- `event_payload` (jsonb)
- `created_at`

---

## 3) API Structure (v1)

Base: `/api/v1`

### Auth/User
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/password-reset`
- `GET /me`
- `PATCH /me`
- `DELETE /me`

### Property
- `POST /properties`
- `GET /properties`
- `GET /properties/:id`
- `PATCH /properties/:id`
- `DELETE /properties/:id`

### Valuation
- `POST /valuations/run` (input: property_id)
- `GET /valuations/:id`
- `GET /properties/:id/valuations/latest`

### Comps
- `GET /comps/search?lat=&lng=&radius=&propertyType=`

### Buyer matching
- `POST /buyer-matching/run` (property_id)
- `GET /properties/:id/buyer-matches`

### Reports
- `POST /reports/generate`
- `GET /reports/:id/download`

### Monetization
- `POST /billing/checkout-session`
- `POST /billing/webhook`
- `GET /billing/subscription`

### Analytics
- `POST /events`

### Admin
- `GET /admin/valuations`
- `PATCH /admin/model-parameters`

---

## 4) Frontend Page Structure

1. **Landing Page**
   - Hero CTA: “Estimate your property value in under 2 minutes”
   - Social proof, sample report screenshot, lead capture.

2. **Login/Register**
   - Email/password + Google/Apple.

3. **Dashboard**
   - Recent properties, last valuation, “Generate report” CTA.

4. **Property Submission Form**
   - Multi-step form with progress indicator.
   - Map pin + address autocomplete.

5. **Property Results Page**
   - Estimated value + range + confidence + “why” explanation.

6. **Comparable Sales Page**
   - Table + map + filters + sold date and DOM.

7. **Buyer Match Dashboard**
   - Match score cards by buyer type + outreach templates.

8. **Saved Properties**
   - Quick revisit and re-run valuation.

9. **Subscription/Billing**
   - Free vs Pro plan, Stripe checkout.

10. **Admin Dashboard**
   - Monitor valuations, override parameters, moderate data.

---

## 5) Valuation Engine Logic (Explainable, Credible)

## Inputs
Property record + market comps + macro indicators ([CITY MARKET DATA], rates, inflation).

## Method A: Sales Comparison (primary weight)
1. Pull comps within distance band (e.g., 1–3 miles).
2. Filter by property type, area variance, age band, condition band.
3. Time decay weighting (recent sales weighted more).
4. Compute adjusted price per sqft:
   - Adjustments for location, condition, size, amenities, floor/view.
5. Weighted median of adjusted comp values.

## Method B: Income Approach (if rental data available)
1. Estimate monthly rent from local rental comps.
2. Annualize NOI with vacancy + expense assumptions.
3. Capitalize via cap rate by neighborhood/property type.

## Method C: Cost Approach (fallback/support)
1. Land value estimate from nearby land comps.
2. Replacement cost by built area × [VALUATION MODEL PARAMETERS].
3. Depreciation by age/condition.

## Final blended value
- Base weights (MVP): Sales 70%, Income 20%, Cost 10%.
- Dynamic reweighting if inputs missing.
- Range = ± (local volatility + comp spread factor).

## Confidence score
- Number of valid comps
- Comp similarity score
- Freshness of market data
- Completeness of input fields

Output confidence as 0–100% with explanation:
- “High confidence due to 12 recent comparable sales within 1.2 miles.”

## Risk indicators
- High market volatility
- Sparse comp data
- Rapid interest rate movement
- Unusual property features

---

## 6) Buyer Matching Logic (Rule-based MVP)

### Scoring dimensions
- Budget fit (30%)
- Location preference fit (25%)
- Property type fit (20%)
- Yield/goal alignment (15%)
- Risk tolerance alignment (10%)

### Match output
- `match_score` (0–100)
- Category label: Strong / Moderate / Weak
- `conversion_likelihood` heuristic
- Suggested outreach message (templated)

Example:
- “This property aligns with rental investors seeking 6–8% yield in [CITY].”

---

## 7) UI Wireframe Descriptions (Mobile-first)

### A) Property form
- Sticky stepper on top.
- Large tap targets, dropdowns, sliders for quality scores.
- “Save draft” button always visible.

### B) Results screen
- Top card: estimated value + confidence badge.
- Tabs: Explanation | Comparables | Buyer Matches | Report.
- CTA: “Download premium PDF report”.

### C) Buyer match
- Horizontal cards by buyer persona.
- One-click “Contact buyer/agent”.

### D) Admin
- KPI tiles: valuation runs/day, report conversion %, avg confidence.

---

## 8) Deployment Checklist

1. Create Supabase project and run migrations.
2. Configure auth provider keys.
3. Add env vars:
   - `DATABASE_URL`
   - `NEXT_PUBLIC_MAP_API_KEY`
   - `STRIPE_SECRET_KEY`
   - `[MLS API]_KEY`
4. Implement API route protection and rate limiting.
5. Set up Stripe products/prices.
6. Deploy to Vercel.
7. Configure custom domain + SSL.
8. Smoke-test:
   - signup/login
   - property create
   - valuation run
   - report checkout/download
9. Enable analytics and error tracking.
10. Publish legal pages (privacy/terms/disclaimer).

---

## 9) Monetization Roadmap (Immediate First)

### Week 1 monetization
- Free basic estimate.
- Paid PDF report ($19–$49).
- “Priority buyer exposure” upsell ($29).

### Week 2+
- Pro subscription for investors/agents (monthly).
- Premium comp analysis package.
- B2B lead-sharing fees with partner agents.

### KPI targets
- Visitor → valuation completion: >20%
- Valuation → paid report: >5%
- CAC payback: <30 days

---

## 10) 14-Day Launch Plan

### Days 1–3
- Set up app skeleton, auth, DB, property form.

### Days 4–6
- Implement valuation engine v1 + comps list + explanations.

### Days 7–8
- PDF report generation + payment flow.

### Days 9–10
- Buyer matching v1 + outreach message templates.

### Days 11–12
- Landing page SEO blocks + analytics + legal docs.

### Day 13
- QA pass (mobile + desktop), fix critical bugs.

### Day 14
- Beta launch + 3-channel acquisition push (SEO + social + partner outreach).

---

## 11) Security & Privacy Checklist

- Passwords hashed (argon2/bcrypt).
- HTTPS everywhere.
- JWT/session hardening (httpOnly, secure cookies).
- Input validation (zod/class-validator).
- SQL injection prevention via ORM parameterization.
- Rate limiting + bot checks on auth and lead forms.
- RBAC for admin endpoints.
- Audit logs for valuation overrides.
- Data minimization + account deletion endpoint.
- Signed URLs for report downloads.
- PII encryption at rest for sensitive fields.

---

## 12) Future Scalability Roadmap

### Phase 2
- Saved searches + alerts.
- AI-generated market commentary.
- Map heatmaps and neighborhood trend overlays.

### Phase 3
- Predictive pricing model using historical series.
- Rental yield optimizer + portfolio analytics.
- Partner API (valuation as a service).

### Technical scaling path
- Split valuation and matching into separate services.
- Add Redis caching for comps queries.
- Add queue workers for heavy report/analytics jobs.
- Read replicas for PostgreSQL.

---

## Assumptions and Constraints

- Market data quality depends on [MLS API] / [PROPERTY DATA API] availability.
- This is an **estimation** product, not certified appraisal software.
- Commercial real estate support deferred to Phase 2 unless mandated.
- Valuation model parameters start heuristic, then calibrated from observed outcomes.

---

## Required Disclaimer Copy (MVP)

“Property valuations provided by this platform are automated estimates for informational purposes only and do not constitute a licensed appraisal, financial advice, or guarantee of sale price. Market conditions and property-specific factors can change rapidly.”
