# API Response Format Changes

All endpoints in the transfer monitor application have been updated to include a consistent `success` field indicating whether the operation succeeded or failed.

## New Response Schema

### BaseResponse[T] - For data responses
```json
{
  "success": true,
  "data": {...},  // The actual response data
  "message": "Operation completed successfully",
  "error": null
}
```

### MessageResponse - For simple action responses
```json
{
  "success": true,
  "message": "Action completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "message": null,  
  "error": "Error description"
}
```

## Files Modified

### 1. New Schema File
- **`app/schemas/base.py`** - Created base response schemas

### 2. Updated Endpoint Files
- **`app/api/v1/endpoints/auth.py`** - All authentication endpoints
- **`app/api/v1/endpoints/users.py`** - User management endpoints  
- **`app/api/v1/endpoints/transfers.py`** - Transfer operation endpoints
- **`app/api/v1/endpoints/wallets.py`** - Wallet management endpoints
- **`app/api/v1/endpoints/admin.py`** - Admin panel endpoints

## Endpoint Changes Summary

### Auth Endpoints (`/api/v1/auth/`)
- `POST /register` → Returns `BaseResponse[UserResponse]`
- `POST /login` → Returns `BaseResponse[Token]`
- `POST /admin/login` → Returns `BaseResponse[Token]`
- `POST /refresh` → Returns `BaseResponse[Token]`
- `POST /send-verification` → Returns `MessageResponse`
- `POST /verify-email` → Returns `BaseResponse[Token]`
- `POST /send-pre-registration-code` → Returns `BaseResponse[dict]`
- `POST /verify-pre-registration-code` → Returns `BaseResponse[dict]`

### User Endpoints (`/api/v1/users/`)
- `GET /me` → Returns `BaseResponse[UserProfile]`
- `PUT /me` → Returns `BaseResponse[UserResponse]`
- `GET /admin/all` → Returns `BaseResponse[List[UserResponse]]`
- `GET /admin/{user_id}` → Returns `BaseResponse[UserProfile]`
- `PUT /admin/{user_id}` → Returns `BaseResponse[UserResponse]`
- `PUT /admin/{user_id}/kyc/{status}` → Returns `MessageResponse`

### Transfer Endpoints (`/api/v1/transfers/`)
- `POST /` → Returns `BaseResponse[TransferResponse]`
- `GET /` → Returns `BaseResponse[List[TransferResponse]]`
- `GET /{transfer_id}` → Returns `BaseResponse[TransferResponse]`
- `GET /{transfer_id}/status` → Returns `BaseResponse[dict]`
- `GET /admin/all` → Returns `BaseResponse[List[TransferResponse]]`
- `PUT /admin/{transfer_id}` → Returns `BaseResponse[TransferResponse]`
- `GET /admin/stats` → Returns `BaseResponse[TransferStats]`

### Wallet Endpoints (`/api/v1/wallets/`)
- `GET /` → Returns `BaseResponse[List[WalletResponse]]`
- `POST /` → Returns `BaseResponse[WalletResponse]`
- `GET /{wallet_id}` → Returns `BaseResponse[WalletResponse]`
- `PUT /{wallet_id}` → Returns `BaseResponse[WalletResponse]`
- `DELETE /{wallet_id}` → Returns `MessageResponse`
- `GET /admin/all` → Returns `BaseResponse[List[WalletResponse]]`
- `PUT /admin/{wallet_id}` → Returns `BaseResponse[WalletResponse]`
- `GET /admin/balances` → Returns `BaseResponse[dict]`

### Admin Endpoints (`/api/v1/admin/`)
- `GET /me` → Returns `BaseResponse[AdminResponse]`
- `PUT /me` → Returns `BaseResponse[AdminResponse]`
- `POST /api-key` → Returns `BaseResponse[dict]`
- `DELETE /api-key` → Returns `MessageResponse`
- `GET /all` → Returns `BaseResponse[List[AdminResponse]]`
- `POST /` → Returns `BaseResponse[AdminResponse]`
- `GET /{admin_id}` → Returns `BaseResponse[AdminResponse]`
- `PUT /{admin_id}` → Returns `BaseResponse[AdminResponse]`
- `DELETE /{admin_id}` → Returns `MessageResponse`
- `GET /dashboard/stats` → Returns `BaseResponse[dict]`

## Breaking Changes

⚠️ **Important**: These changes are breaking changes for any existing frontend applications consuming the API.

### Before:
```json
{
  "id": "123",
  "email": "user@example.com",
  "first_name": "John"
}
```

### After:
```json
{
  "success": true,
  "data": {
    "id": "123", 
    "email": "user@example.com",
    "first_name": "John"
  },
  "message": "User retrieved successfully"
}
```

## Frontend Integration

Frontend applications will need to be updated to:

1. **Check the `success` field** before processing data
2. **Access actual data via the `data` field**
3. **Handle error responses** using the `error` field
4. **Display messages** from the `message` field

### Example Frontend Code:
```javascript
const response = await fetch('/api/v1/users/me');
const result = await response.json();

if (result.success) {
  // Handle successful response
  const userData = result.data;
  console.log(result.message); // Show success message
} else {
  // Handle error
  console.error(result.error); // Show error message
}
```

## Benefits

1. **Consistent API responses** across all endpoints
2. **Better error handling** with structured error responses
3. **Improved debugging** with descriptive success/error messages
4. **Type safety** with TypeScript/Pydantic models
5. **Future-proof** API design following REST best practices

All endpoints now follow the same response pattern, making the API more predictable and easier to work with for frontend developers.