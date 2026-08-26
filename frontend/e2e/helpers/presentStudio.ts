import { expect, type Page } from "@playwright/test";

/** Dashboard → layout picker → create blank deck → studio editor. */
export async function openBlankPresentationStudio(page: Page) {
  await page.getByTestId("present-blank").click();
  await expect(page.getByTestId("present-blank-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("present-blank-create").click();
  await expect(page.getByTestId("present-studio")).toBeVisible({ timeout: 25_000 });
  await expect(page.getByTestId("present-editor")).toBeVisible({ timeout: 15_000 });
}

/** Speaker notes live on the Properties rail tab in studio edit mode. */
export async function fillSpeakerNotes(page: Page, text: string) {
  await page.getByTestId("present-editor-tab-layers").click();
  const notes = page.getByTestId("present-editor-notes");
  await expect(notes).toBeVisible({ timeout: 10_000 });
  await notes.fill(text);
}

/** Double-click a canvas text block, then type replacement copy. */
export async function editCanvasTextBlock(page: Page, text: string) {
  const hit = page.locator('[data-testid^="present-editor-block-hit-"]').first();
  await expect(hit).toBeVisible({ timeout: 10_000 });
  await hit.dblclick();
  const inline = page.locator('[data-testid^="present-editor-inline-"]').first();
  await expect(inline).toBeVisible({ timeout: 5_000 });
  await inline.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(text);
}
