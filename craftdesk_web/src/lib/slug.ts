/**
 * CraftDesk Web — Client-side URL slug utilities.
 */

export function slugifyShopName(name: string): string {

  if (!name) return "shop";
  return name
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-+|-+$/g, "") || "shop";
}
