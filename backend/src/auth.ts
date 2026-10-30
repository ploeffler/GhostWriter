import { createRemoteJWKSet, jwtVerify, type JWTPayload } from "jose";

export interface AuthConfig {
  AUTH0_ISSUER?: string;
  AUTH0_AUDIENCE?: string;
}

export interface AuthenticatedUser {
  subject: string;
  scopes: string[];
  claims: JWTPayload;
}

const jwksCache = new Map<string, ReturnType<typeof createRemoteJWKSet>>();

function getJwks(issuer: string) {
  const cached = jwksCache.get(issuer);
  if (cached) return cached;
  const jwks = createRemoteJWKSet(new URL(".well-known/jwks.json", issuer));
  jwksCache.set(issuer, jwks);
  return jwks;
}

export async function authenticateRequest(
  request: Request,
  env: AuthConfig
): Promise<AuthenticatedUser | null> {
  if (!env.AUTH0_ISSUER || !env.AUTH0_AUDIENCE) return null;

  let issuer: URL;
  try {
    issuer = new URL(env.AUTH0_ISSUER);
  } catch {
    return null;
  }
  if (issuer.protocol !== "https:" || !issuer.pathname.endsWith("/")) return null;

  const header = request.headers.get("authorization");
  const match = header?.match(/^Bearer ([^\s]+)$/i);
  if (!match) return null;

  try {
    const { payload } = await jwtVerify(match[1], getJwks(issuer.toString()), {
      issuer: issuer.toString(),
      audience: env.AUTH0_AUDIENCE,
      algorithms: ["RS256"]
    });
    if (typeof payload.sub !== "string" || !payload.sub) return null;

    const scopes = typeof payload.scope === "string"
      ? payload.scope.split(/\s+/).filter(Boolean)
      : [];
    return { subject: payload.sub, scopes, claims: payload };
  } catch {
    return null;
  }
}

export function hasScope(user: AuthenticatedUser, required: string): boolean {
  return user.scopes.includes(required);
}
