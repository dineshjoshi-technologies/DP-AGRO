/**
 * Exceptions for DJ Tech Agent Runtime SDK
 */

export class DJTechError extends Error {
  public readonly details: Record<string, unknown>;

  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'DJTechError';
    this.details = details;
    
    // Maintains proper stack trace in V8 environments
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, DJTechError);
    }
  }
}

export class APIError extends DJTechError {
  public readonly statusCode: number;
  public readonly code?: string;

  constructor(
    message: string,
    statusCode: number,
    code?: string,
    details: Record<string, unknown> = {}
  ) {
    super(message, details);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.code = code;
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, APIError);
    }
  }
}

export class AuthenticationError extends APIError {
  constructor(message = 'Authentication failed', details: Record<string, unknown> = {}) {
    super(message, 401, 'AUTHENTICATION_ERROR', details);
    this.name = 'AuthenticationError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AuthenticationError);
    }
  }
}

export class AuthorizationError extends APIError {
  constructor(message = 'Access denied', details: Record<string, unknown> = {}) {
    super(message, 403, 'AUTHORIZATION_ERROR', details);
    this.name = 'AuthorizationError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, AuthorizationError);
    }
  }
}

export class NotFoundError extends APIError {
  constructor(message = 'Resource not found', details: Record<string, unknown> = {}) {
    super(message, 404, 'NOT_FOUND', details);
    this.name = 'NotFoundError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, NotFoundError);
    }
  }
}

export class ValidationError extends APIError {
  constructor(message = 'Validation failed', details: Record<string, unknown> = {}) {
    super(message, 400, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ValidationError);
    }
  }
}

export class ConflictError extends APIError {
  constructor(message = 'Resource conflict', details: Record<string, unknown> = {}) {
    super(message, 409, 'CONFLICT', details);
    this.name = 'ConflictError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ConflictError);
    }
  }
}

export class RateLimitError extends APIError {
  public readonly retryAfter?: number;

  constructor(
    message = 'Rate limit exceeded',
    retryAfter?: number,
    details: Record<string, unknown> = {}
  ) {
    super(message, 429, 'RATE_LIMIT', details);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, RateLimitError);
    }
  }
}

export class ServerError extends APIError {
  constructor(message = 'Internal server error', statusCode = 500, details: Record<string, unknown> = {}) {
    super(message, statusCode, 'SERVER_ERROR', details);
    this.name = 'ServerError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ServerError);
    }
  }
}

export class TimeoutError extends DJTechError {
  constructor(message = 'Request timed out', details: Record<string, unknown> = {}) {
    super(message, details);
    this.name = 'TimeoutError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, TimeoutError);
    }
  }
}

export class NetworkError extends DJTechError {
  constructor(message = 'Network error', details: Record<string, unknown> = {}) {
    super(message, details);
    this.name = 'NetworkError';
    
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, NetworkError);
    }
  }
}

export function mapHttpError(
  statusCode: number,
  message: string,
  code?: string,
  details: Record<string, unknown> = {}
): APIError {
  switch (statusCode) {
    case 400:
      return new ValidationError(message, details);
    case 401:
      return new AuthenticationError(message, details);
    case 403:
      return new AuthorizationError(message, details);
    case 404:
      return new NotFoundError(message, details);
    case 409:
      return new ConflictError(message, details);
    case 429:
      return new RateLimitError(message, undefined, details);
    default:
      if (statusCode >= 500) {
        return new ServerError(message, statusCode, details);
      }
      return new APIError(message, statusCode, code, details);
  }
}