import type { UserInfo } from '~/types/user-info';

/** Drops unnecessary fields from a given user information. */
export function stripUserInfo(user: UserInfo): UserInfo {
  return {
    name: user.name,
    preferredUsername: user.preferredUsername,
    summary: user.summary,
    url: user.url,
    followerCount: user.followerCount,
    followingCount: user.followingCount,
    createdAt: user.createdAt,
    lastActivityAt: user.lastActivityAt,
  };
}
