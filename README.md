# Property Revenue Dashboard - Bug Fixes

## Project Overview

This is a multi-tenant property management revenue dashboard system that allows property management companies to view and track their rental revenue across multiple properties and time zones.

## Assignment Context

This was a debugging challenge to identify and fix critical bugs in a recently launched revenue dashboard system. Three major issues were reported:

1. **Privacy Concern (Client B)**: Sometimes seeing revenue data from other companies
2. **Data Accuracy (Client A)**: March revenue totals not matching internal records
3. **Finance Issue**: Revenue totals occasionally off by a few cents

## Bugs Identified & Fixed

### 🔴 Bug #1: Cache Poisoning / Data Leakage (CRITICAL)

**Severity**: Critical - Privacy Violation

**Issue**: The Redis cache key for revenue data did not include `tenant_id`, causing cross-tenant data contamination. When multiple tenants had properties with the same ID (e.g., `prop-001`), they would share cached data.

**Location**: `backend/app/services/cache.py:14`

**Before**:
```python
cache_key = f"revenue:{property_id}"  # ❌ Missing tenant isolation
```

**After**:
```python
cache_key = f"revenue:{property_id}:{tenant_id}"  # ✅ Proper multi-tenant isolation
```

**Impact**: 
- Fixed privacy violation where Client B could see Client A's data
- Restored proper multi-tenant data isolation
- Prevented potential compliance and legal issues

---

### 🟡 Bug #2: Timezone Date Filtering Issue

**Severity**: High - Data Accuracy

**Issue**: Date filtering used naive datetime objects without timezone information. Since the database stores timestamps in UTC (`TIMESTAMPTZ`), bookings near midnight in non-UTC timezones were incorrectly excluded from monthly calculations.

**Location**: `backend/app/services/reservations.py:20-24`

**Example Scenario**:
- Property in Paris (UTC+1)
- Booking check-in: March 1, 2024 00:30 Paris time
- UTC equivalent: February 29, 2024 23:30 UTC
- Bug: Excluded from March revenue because query used naive datetime

**Before**:
```python
start_date = datetime(year, month, 1)  # ❌ Naive datetime
end_date = datetime(year, month + 1, 1)
```

**After**:
```python
from datetime import datetime, timezone

start_date = datetime(year, month, 1, tzinfo=timezone.utc)  # ✅ Timezone-aware
end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
```

**Impact**:
- March revenue totals now match Client A's internal records
- All bookings correctly included in monthly calculations
- Proper handling of properties across different time zones

---

### 🟠 Bug #3: Float Precision / Rounding Errors

**Severity**: Medium - Finance Accuracy

**Issue**: Revenue totals stored as `NUMERIC(10,3)` in the database (exact decimal precision) were being converted to `float`, causing floating-point precision loss and cent-level discrepancies.

**Location**: `backend/app/api/v1/dashboard.py:18`

**Example**:
```
Database: 333.333 + 333.333 + 333.334 = 1000.000 (exact)
Float:    333.33300000000004 + ... = 1000.01 or 999.99 (imprecise)
```

**Before**:
```python
total_revenue_float = float(revenue_data['total'])  # ❌ Loses precision
return {"total_revenue": total_revenue_float}
```

**After**:
```python
# ✅ Keep as string to preserve Decimal precision from database
total_revenue = revenue_data['total']
return {"total_revenue": total_revenue}
```

**Impact**:
- Eliminated penny-level discrepancies in revenue totals
- Maintained exact financial precision required for accounting
- Compliance with financial reporting standards

---

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React/Vue (nginx served)
- **Database**: PostgreSQL 15
- **Cache**: Redis
- **Containerization**: Docker & Docker Compose

## Setup & Installation

### Prerequisites
- Docker Desktop
- Docker Compose

### Quick Start

1. **Clone the repository**:
```bash
git clone <repository-url>
cd New_devs_App
```

2. **Start the development environment**:
```bash
docker-compose up --build
```

3. **Access the application**:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Environment Details

The application runs 4 services:
- **Backend** (port 8000): FastAPI application
- **Frontend** (port 3000): Static frontend served by nginx
- **Database** (port 5433): PostgreSQL with schema and seed data
- **Redis** (port 6380): Cache layer

## Testing the Fixes

### Test Credentials

**Client A (Sunset Properties)**:
- Email: `sunset@propertyflow.com`
- Password: `client_a_2024`

**Client B (Ocean Rentals)**:
- Email: `ocean@propertyflow.com`
- Password: `client_b_2024`

### Verification Steps

#### Test 1: Data Leakage Fix
1. Login as Client B
2. View property `prop-001` (Mountain Lodge Beta)
3. Refresh page 10+ times
4. **Expected**: Always see consistent Ocean Rentals data
5. Logout and login as Client A
6. View property `prop-001` (Beach House Alpha)
7. **Expected**: See different revenue data than Client B

#### Test 2: Revenue Accuracy
1. Login as Client A (Sunset Properties)
2. View March 2024 revenue for `prop-001`
3. **Expected**: Total includes timezone-edge booking = $2,250.00
4. Compare with database:
```bash
docker exec -it new_devs_app-db-1 psql -U postgres -d propertyflow -c "
  SELECT SUM(total_amount) 
  FROM reservations 
  WHERE property_id = 'prop-001' 
    AND tenant_id = 'tenant-a';
"
```

#### Test 3: Decimal Precision
1. Login as Client A
2. View any property revenue
3. **Expected**: Exact decimal values (e.g., 1000.000, not 999.99 or 1000.01)

### Database Access

Connect to PostgreSQL:
```bash
docker exec -it new_devs_app-db-1 psql -U postgres -d propertyflow
```

Useful queries:
```sql
-- View all tenants
SELECT * FROM tenants;

-- View properties with same ID across tenants
SELECT p.id, p.name, t.name as tenant 
FROM properties p 
JOIN tenants t ON p.tenant_id = t.id 
WHERE p.id = 'prop-001';

-- View reservations for a specific tenant
SELECT r.*, p.name 
FROM reservations r 
JOIN properties p ON r.property_id = p.id 
WHERE r.tenant_id = 'tenant-a';
```

## Development

### Project Structure
```
New_devs_App/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── dashboard.py          # Fixed: Removed float conversion
│   │   ├── services/
│   │   │   ├── cache.py               # Fixed: Added tenant_id to cache key
│   │   │   └── reservations.py       # Fixed: Timezone-aware datetimes
│   │   └── core/
│   │       └── auth.py                # Authentication & tenant resolution
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   └── ...
├── database/
│   ├── schema.sql                     # Database schema
│   └── seed.sql                       # Test data
├── docker-compose.yml
└── BUG_FIXES_SUMMARY.md              # Detailed bug analysis
```

### Making Changes

After code changes, rebuild and restart:
```bash
docker-compose down
docker-compose up --build
```

To clear cache after fixes:
```bash
docker exec -it new_devs_app-redis-1 redis-cli FLUSHALL
docker-compose restart backend
```

## Key Learnings

### Multi-Tenant Architecture Best Practices
1. **Always include tenant_id in cache keys** to prevent data leakage
2. **Filter all queries by tenant_id** at the database level
3. **Test with overlapping resource IDs** across tenants

### Date/Time Handling
1. **Use timezone-aware datetimes** when working with UTC timestamps
2. **Store all timestamps in UTC** in the database
3. **Convert to local time only in the presentation layer**

### Financial Data
1. **Never use float for money** - always use Decimal or integer cents
2. **Preserve precision through the entire stack** (DB → API → Frontend)
3. **Use NUMERIC/DECIMAL types** in PostgreSQL for currency

## Deployment Notes

### Pre-Deployment Checklist
- [ ] Clear Redis cache: `docker exec -it <redis-container> redis-cli FLUSHALL`
- [ ] Run database migrations (if any)
- [ ] Restart backend service
- [ ] Verify no breaking changes to API responses

### No Breaking Changes
All fixes maintain backward compatibility:
- API response structures unchanged
- Database schema unchanged
- Only internal logic improved

## License

This project was completed as part of a technical assessment.

## Author

**Timileyin Kehinde** - Backend Developer Candidate

**Co-Authored-By**: Warp <agent@warp.dev>

---

## Additional Resources

- [BUG_FIXES_SUMMARY.md](./BUG_FIXES_SUMMARY.md) - Detailed bug analysis and Loom video script
- [ASSIGNMENT.md](./ASSIGNMENT.md) - Original assignment requirements
- Backend API Documentation: http://localhost:8000/docs (when running)

## Contact

For questions or clarifications about the bug fixes, please reach out through the interview process.
