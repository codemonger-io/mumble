/** User information. */
export interface UserInfo {
  /** Name of the user. */
  name: string;

  /** Preferred username of the user. */
  preferredUsername: string;

  /** Summary about the user. */
  summary: string;

  /** URL associated with the user. */
  url: string;

  /** Number of followers of the user. */
  followerCount: number;

  /** Number of users followed by the user. */
  followingCount: number;

  /** When the user was created (yyyy-mm-ddTHH:MM:ss.SSSSSSZ). */
  createdAt: string;

  /** Last activity datetime (yyyy-mm-ddTHH:MM:ss.SSSSSSZ) of the user. */
  lastActivityAt: string;
}
