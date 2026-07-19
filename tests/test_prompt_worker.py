"""
Unit and integration tests for the PromptWorker.

Unit tests verify parsing and validation logic without API calls.
Integration tests (marked with @pytest.mark.integration) call the Gemini API.

Run unit tests:
    pytest tests/test_prompt_worker.py -v -k "not integration"

Run integration tests:
    pytest tests/test_prompt_worker.py -v -k "integration"
"""

from __future__ import annotations

import pytest

from etsy_pipeline.models.job import Job, JobStatus
from etsy_pipeline.utils.exceptions import PromptParsingError, PromptValidationError
from etsy_pipeline.workers.prompt_worker import PromptWorker
from etsy_pipeline.workers.prompt_worker_config import LOCKED_SECTIONS

# =============================================================
# FIXTURES
# =============================================================


@pytest.fixture
def worker() -> PromptWorker:
    """Create a PromptWorker instance for testing."""
    return PromptWorker()


@pytest.fixture
def sample_job() -> Job:
    """Create a sample Job for testing."""
    return Job(theme="Lilo & Stitch", event_type="birthday")


@pytest.fixture
def sample_gemini_response() -> str:
    """Sample Gemini response mimicking SKILL.md output format."""
    return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 LittleNest PROMPT BATCH — Lilo & Stitch | Birthday
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAIN_CHARACTER: Stitch (Experiment 626, blue alien with large ears)
SUB_CHARACTER_1: Lilo Pelekai (Hawaiian girl, dark hair, red floral dress)
SUB_CHARACTER_2: Angel (Experiment 624, pink alien)

## MAIN_CHARACTER

1. Stitch, Experiment 626 from Lilo & Stitch, blue alien with large ears and koala-like features, sitting upright holding a colorful birthday cake with lit candles in both paws, birthday cake prominently visible and centered, face forward, wide toothy smile, eyes sparkling and defined, full body visible from head to toe, exactly four legs, all four paws clearly grounded, correct quadruped anatomy, no extra legs, no missing legs, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark, no background elements

2. Stitch, Experiment 626, wearing a party hat centered between his large ears, sitting cross-legged, party hat clearly visible, arms resting on knees, face forward, playful toothy grin, tongue slightly out, full body visible from head to toe, exactly four legs, all four paws clearly grounded, correct quadruped anatomy, soft watercolor illustration style, soft blue and pink palette, isolated subject, pure white background, no text, no watermark

3. Stitch, Experiment 626, standing upright holding a cluster of pastel balloons, balloons floating above his head, face forward, excited wide grin, full body visible from head to toe, exactly four legs, all four paws clearly grounded, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

4. Stitch, Experiment 626, sitting with a wrapped pink birthday gift, ribbon bow on top, gift at chest level, face forward, mischievous smile, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

5. Stitch, Experiment 626, holding a cupcake with a candle, sitting upright, cupcake at face level, face forward, licking lips, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

6. Stitch, Experiment 626, wearing a crown, sitting on a decorated birthday throne, face forward, proud smile, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

7. Stitch, Experiment 626, blowing a party horn, sitting upright, party horn clearly visible, face forward, cheeks puffed, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

8. Stitch, Experiment 626, holding a lollipop, standing upright, lollipop at face level, face forward, tongue out reaching for candy, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

9. Stitch, Experiment 626, sitting inside a large gift box, peeking out, box decorated with polka dots, face forward, playful smile, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

10. Stitch, Experiment 626, playing ukulele wearing a birthday hat, sitting cross-legged, ukulele clearly rendered, face forward, happy smile with eyes closed, full body visible, correct quadruped anatomy, soft watercolor illustration style, pastel blue palette, isolated subject, pure white background, no text, no watermark

## SUB_CHARACTER_1

1. Lilo Pelekai, Hawaiian girl with dark hair in two buns, wearing her red floral dress, standing upright holding a cluster of pastel balloons on strings in her right hand, balloons clearly visible floating above her hand, face forward, wide open excited smile, full body visible from head to toe, exactly two arms, exactly two legs, correct human anatomy, no extra limbs, hands correctly rendered with five fingers each, soft watercolor illustration style, warm tropical pastel palette, isolated subject, pure white background, no text, no watermark, no background elements

2. Lilo Pelekai, in her red floral dress, carrying a large pink wrapped gift box with a ribbon bow, gift box clearly held in both arms at chest, standing upright facing forward, barefoot, face forward, happy grin eyes sparkling, full body visible from head to toe, exactly two arms, exactly two legs, correct human anatomy, no extra limbs, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

3. Lilo Pelekai, in her red floral dress, blowing out candles on a birthday cake, cake on table in front, leaning forward, face forward, pursed lips blowing, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

4. Lilo Pelekai, wearing a flower lei and her red floral dress, dancing hula, arms in gentle hula position, face forward, joyful smile, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

5. Lilo Pelekai, in her red floral dress, holding a pineapple decorated with a birthday candle, standing upright, face forward, happy smile, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

6. Lilo Pelekai, in her red floral dress, sitting with a slice of birthday cake on a plate, plate on her lap, face forward, satisfied smile, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

7. Lilo Pelekai, in her red floral dress, holding an ice cream cone with sprinkles, standing upright, ice cream at face level, face forward, delighted expression, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

8. Lilo Pelekai, in her red floral dress, wearing a birthday crown, standing upright with hands on hips, face forward, confident happy smile, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

9. Lilo Pelekai, in her red floral dress, holding a camera taking a photo, camera at eye level, standing upright, face forward visible beside camera, curious expression, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

10. Lilo Pelekai, in her red floral dress, holding confetti in both hands throwing it upward, confetti scattered above, standing upright, face forward, overjoyed laughing expression, full body visible, correct human anatomy, soft watercolor illustration style, tropical pastel tones, isolated subject, pure white background, no text, no watermark

## SUB_CHARACTER_2

1. Angel, Experiment 624 from Lilo & Stitch, pink alien with long antennae, standing upright, holding a heart-shaped balloon, face forward, sweet smile, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

2. Angel, Experiment 624, pink alien, sitting with a birthday cupcake, cupcake held in both paws, face forward, happy expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

3. Angel, Experiment 624, pink alien, wearing a small tiara, standing upright, paws clasped together, face forward, gentle smile, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

4. Angel, Experiment 624, pink alien, holding a hibiscus flower, standing upright, flower at chest level, face forward, sweet expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

5. Angel, Experiment 624, pink alien, blowing a kiss, standing upright, one paw near mouth, face forward, adorable expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

6. Angel, Experiment 624, pink alien, sitting with a wrapped birthday gift, gift on lap, face forward, excited expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

7. Angel, Experiment 624, pink alien, holding a party streamer, standing upright, streamer flowing, face forward, playful smile, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

8. Angel, Experiment 624, pink alien, sitting on a cloud of cotton candy, face forward, dreamy expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

9. Angel, Experiment 624, pink alien, holding a small ukulele, standing upright, ukulele at chest, face forward, singing expression, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

10. Angel, Experiment 624, pink alien, wearing a birthday hat, sitting upright, paws resting on knees, face forward, content smile, full body visible, correct anatomy, soft watercolor illustration style, pastel pink palette, isolated subject, pure white background, no text, no watermark

## SUB_CHARACTER_3

(not applicable for this roster)

## SUB_CHARACTER_4

(not applicable for this roster)

## SUB_CHARACTER_5

(not applicable for this roster)

## SUB_CHARACTER_6

(not applicable for this roster)

## SUB_CHARACTER_7

(not applicable for this roster)

## SUB_CHARACTER_8

(not applicable for this roster)

## CHARACTER_COMBO_2

1. Stitch, Experiment 626, and Lilo Pelekai in her red floral dress, sitting side by side sharing a slice of birthday cake, both characters fully visible head to toe, facing forward, Stitch with a toothy grin and Lilo with a wide happy smile, Stitch with correct quadruped anatomy, Lilo with exactly two arms exactly two legs and correct human anatomy, soft watercolor illustration style, pastel blue and tropical pink palette, isolated subject, pure white background, no text, no watermark

2. Stitch and Lilo, hugging each other, both facing forward, Stitch with arms around Lilo, both smiling warmly, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

3. Stitch and Lilo, both wearing birthday hats, standing side by side, both facing forward, matching excited expressions, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

4. Stitch and Lilo, high-fiving each other, standing facing each other but bodies angled toward viewer, both smiling, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

5. Stitch and Lilo, sitting together sharing an ice cream sundae, sundae between them, both facing forward, both with happy expressions, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

6. Stitch and Lilo, both blowing party horns, standing side by side, confetti around them, facing forward, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

7. Stitch and Lilo, playing ukulele together, sitting cross-legged, one ukulele between them, facing forward, both singing with smiles, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

8. Stitch and Lilo, dancing together, gentle hula pose, facing forward, joyful expressions, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

9. Stitch and Lilo, holding a birthday banner between them, standing side by side, banner stretched between their hands, facing forward, proud smiles, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

10. Stitch and Lilo, both sitting on a surfboard decorated with birthday decorations, facing forward, both with adventurous smiles, full body visible, correct anatomy for both, soft watercolor illustration style, pastel blue and pink palette, isolated subject, pure white background, no text, no watermark

## CHARACTER_COMBO_3

1. Stitch, Lilo, and Angel together, standing in a line, all facing forward, Stitch in center with Lilo on left and Angel on right, all smiling, full body visible, correct anatomy for all three, soft watercolor illustration style, pastel blue pink and tropical palette, isolated subject, pure white background, no text, no watermark

2. Stitch, Lilo, and Angel, sitting together around a birthday cake, all facing forward, each with unique expressions, full body visible, correct anatomy for all three, soft watercolor illustration style, pastel blue pink and tropical palette, isolated subject, pure white background, no text, no watermark

3. Stitch, Lilo, and Angel, group hug, all facing forward, arms around each other, all smiling warmly, full body visible, correct anatomy for all, soft watercolor illustration style, pastel blue pink and tropical palette, isolated subject, pure white background, no text, no watermark

4. Stitch, Lilo, and Angel, all wearing birthday hats, standing together, facing forward, waving, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

5. Stitch, Lilo, and Angel, holding balloons together, each with a different colored balloon, standing side by side, facing forward, happy expressions, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

6. Stitch, Lilo, and Angel, having a tea party with cupcakes, sitting around a small table, all facing forward, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

7. Stitch, Lilo, and Angel, dancing together in celebration, gentle poses, all facing forward, joyful expressions, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

8. Stitch, Lilo, and Angel, sharing presents, each holding a gift, standing together, facing forward, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

9. Stitch, Lilo, and Angel, sitting on a beach blanket with party decorations, all facing forward, relaxed happy expressions, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

10. Stitch, Lilo, and Angel, blowing confetti from their hands, standing together, confetti swirling above, all facing forward, overjoyed expressions, full body visible, correct anatomy for all, soft watercolor illustration style, pastel palette, isolated subject, pure white background, no text, no watermark

## CHARACTER_COMBO_4

(not applicable for this roster)

## CHARACTER_COMBO_FULL_GROUP

(not applicable for this roster)

## PATTERN

1. Seamless repeat pattern, blue hibiscus flowers and pink hibiscus flowers tossed layout with small tropical leaves, pastel blue pink and white palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

2. Seamless repeat pattern, surfboards and coconuts with ocean wave motifs in tossed layout, pastel blue mint and sand palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

3. Seamless repeat pattern, tropical monstera leaves and plumeria flowers in tossed layout, pastel green pink and white palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

4. Seamless repeat pattern, birthday balloons confetti and stars in tossed layout, pastel blue pink yellow palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

5. Seamless repeat pattern, ukuleles and hibiscus flowers in tossed layout, warm honey blue and pink palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

6. Seamless repeat pattern, pineapples and tropical flowers in grid layout, pastel yellow green and pink palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

7. Seamless repeat pattern, seashells and starfish with coral motifs in tossed layout, pastel blue sand and coral palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

8. Seamless repeat pattern, small birthday cakes and cupcakes in tossed layout, pastel pink blue and lavender palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

9. Seamless repeat pattern, hearts and flowers with polka dot accents in tossed layout, pastel pink blue and white palette, soft watercolor illustration style, white background, no characters, no text, no watermark, evenly spaced, tileable

10. Seamless repeat pattern, tropical fish and bubbles in tossed layout, pastel blue turquoise and coral palette, soft watercolor illustration style, light blue background, no characters, no text, no watermark, evenly spaced, tileable

## PROP

1. Ukulele with floral hibiscus decoration on the body, isolated clipart, centered, warm honey wood color, pink and blue flower detail, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

2. Birthday cake with tropical flower decorations, three tiers, pastel blue pink and white frosting, isolated clipart, centered, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

3. Pink hibiscus flower in full bloom, large petals, dew drops on edges, isolated clipart, centered, soft watercolor illustration style, pastel pink palette, white background, no characters, no text, no watermark

4. Surfboard with tropical floral pattern, standing upright, blue and pink color scheme, isolated clipart, centered, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

5. Birthday balloon cluster, five balloons in pastel blue pink yellow lavender mint, with curly ribbons, isolated clipart, centered, soft watercolor illustration style, pastel palette, white background, no characters, no text, no watermark

6. Pineapple wearing a tiny birthday crown, golden yellow fruit with green leaves, isolated clipart, centered, soft watercolor illustration style, tropical warm palette, white background, no characters, no text, no watermark

7. Coconut drink with a straw and small umbrella, decorated with a hibiscus flower, isolated clipart, centered, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

8. Wrapped birthday gift box with tropical floral wrapping paper and bow, isolated clipart, centered, pastel pink blue, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

9. Plumeria flower lei necklace arranged in a circle, white and yellow flowers, isolated clipart, centered, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

10. Birthday cupcake with a palm tree topper, pastel blue frosting with sprinkles, isolated clipart, centered, soft watercolor illustration style, tropical pastel palette, white background, no characters, no text, no watermark

## SCENE

1. Hawaiian beach scene, soft turquoise ocean meeting golden sand shore, palm trees on the sides, rainbow in the sky, plumeria flowers scattered on sand, dreamy soft light, watercolor illustration style, tropical pastel palette, no characters in foreground, no text, no watermark

2. Tropical garden party scene, string lights and paper lanterns, flower garlands, a decorated table with cake in the distance, lush green tropical plants, dreamy soft light, watercolor illustration style, tropical pastel palette, no characters in foreground, no text, no watermark

3. Sunset beach scene, orange pink and purple sky, silhouette of palm trees, gentle waves, birthday banner strung between palm trees in distance, dreamy soft light, watercolor illustration style, warm tropical palette, no characters in foreground, no text, no watermark

4. Hawaiian cottage scene, small blue wooden house with a porch, surrounded by tropical flowers and plants, tiki torches, warm golden light, watercolor illustration style, tropical pastel palette, no characters in foreground, no text, no watermark

5. Underwater ocean scene, coral reef with colorful tropical fish, bubbles and light rays filtering through water, soft dreamy atmosphere, watercolor illustration style, pastel blue and coral palette, no characters in foreground, no text, no watermark

6. Tropical jungle scene, lush green canopy, hanging vines, exotic flowers, butterflies, soft filtered sunlight, watercolor illustration style, green and pastel palette, no characters in foreground, no text, no watermark

7. Beach bonfire scene at dusk, small fire on sand, tiki torches around, stars beginning to appear, gentle waves in background, watercolor illustration style, warm orange and blue palette, no characters in foreground, no text, no watermark

8. Hawaiian flower shop scene, colorful flower arrangements in baskets, lei making station, tropical decor, warm inviting atmosphere, watercolor illustration style, tropical pastel palette, no characters in foreground, no text, no watermark

9. Tropical waterfall scene, cascading water into a blue lagoon, surrounded by lush ferns and tropical flowers, misty atmosphere, watercolor illustration style, green and blue pastel palette, no characters in foreground, no text, no watermark

10. Birthday party decorated beach pavilion, white canopy with tropical flower garlands, cake table in center, ocean view in background, dreamy soft light, watercolor illustration style, pastel blue pink and white palette, no characters in foreground, no text, no watermark

## LOGO_EMBLEM

(not applicable for this roster)

## BANNER

(not applicable for this roster)

## ALPHABET_NUMBER

(not applicable for this roster)

## FRAME_BORDER

(not applicable for this roster)
"""


# =============================================================
# UNIT TESTS — Parsing
# =============================================================


class TestParseResponse:
    """Test the _parse_response method."""

    def test_parses_all_sections(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify all locked sections are present in parsed output."""
        prompts, roster = worker._parse_response(sample_gemini_response)

        for section in LOCKED_SECTIONS:
            assert section in prompts, f"Missing section: {section}"

    def test_active_sections_have_prompts(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify active sections contain at least 10 prompts."""
        prompts, _ = worker._parse_response(sample_gemini_response)

        active_sections = ["MAIN_CHARACTER", "SUB_CHARACTER_1", "SUB_CHARACTER_2",
                          "CHARACTER_COMBO_2", "CHARACTER_COMBO_3", "PATTERN", "PROP", "SCENE"]

        for section in active_sections:
            assert len(prompts[section]) >= 10, (
                f"Section {section} has {len(prompts[section])} prompts (expected >= 10)"
            )

    def test_inactive_sections_are_empty(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify inactive sections have empty prompt lists."""
        prompts, _ = worker._parse_response(sample_gemini_response)

        inactive_sections = [
            "SUB_CHARACTER_3", "SUB_CHARACTER_4", "SUB_CHARACTER_5",
            "SUB_CHARACTER_6", "SUB_CHARACTER_7", "SUB_CHARACTER_8",
            "CHARACTER_COMBO_4", "CHARACTER_COMBO_FULL_GROUP",
            "LOGO_EMBLEM", "BANNER", "ALPHABET_NUMBER", "FRAME_BORDER",
        ]

        for section in inactive_sections:
            assert prompts[section] == [], f"Section {section} should be empty but has {len(prompts[section])} prompts"

    def test_prompts_are_clean_strings(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify prompts are clean single-line strings without numbering."""
        prompts, _ = worker._parse_response(sample_gemini_response)

        for section, section_prompts in prompts.items():
            for prompt in section_prompts:
                assert isinstance(prompt, str)
                assert not prompt.startswith(("1.", "2.", "3.")), (
                    f"Prompt in {section} still has numbering prefix: {prompt[:50]}"
                )
                assert prompt.strip() == prompt, f"Prompt has leading/trailing whitespace in {section}"

    def test_roster_extraction(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify character roster is extracted from preamble."""
        _, roster = worker._parse_response(sample_gemini_response)

        assert "MAIN_CHARACTER" in roster
        assert "Stitch" in roster["MAIN_CHARACTER"]
        assert "SUB_CHARACTER_1" in roster
        assert "Lilo" in roster["SUB_CHARACTER_1"]
        assert "SUB_CHARACTER_2" in roster
        assert "Angel" in roster["SUB_CHARACTER_2"]

    def test_empty_response_raises_error(self, worker: PromptWorker) -> None:
        """Verify empty response raises PromptParsingError."""
        with pytest.raises(PromptParsingError, match="No valid section headings"):
            worker._parse_response("")

    def test_garbage_response_raises_error(self, worker: PromptWorker) -> None:
        """Verify non-structured response raises PromptParsingError."""
        with pytest.raises(PromptParsingError, match="No valid section headings"):
            worker._parse_response("This is just random text without any sections.")


# =============================================================
# UNIT TESTS — Validation
# =============================================================


class TestValidatePrompts:
    """Test the _validate_prompts method."""

    def test_valid_prompts_pass(self, worker: PromptWorker, sample_gemini_response: str) -> None:
        """Verify valid prompts pass validation."""
        prompts, _ = worker._parse_response(sample_gemini_response)
        # Should not raise
        worker._validate_prompts(prompts)

    def test_all_empty_sections_raises_error(self, worker: PromptWorker) -> None:
        """Verify all-empty prompts raises PromptValidationError."""
        empty_prompts = {section: [] for section in LOCKED_SECTIONS}

        with pytest.raises(PromptValidationError, match="No prompts were extracted"):
            worker._validate_prompts(empty_prompts)

    def test_missing_sections_are_added(self, worker: PromptWorker) -> None:
        """Verify missing sections are added as empty lists."""
        partial_prompts = {
            "MAIN_CHARACTER": ["prompt 1", "prompt 2"],
        }

        # Should not raise (has at least some prompts)
        worker._validate_prompts(partial_prompts)

        # Missing sections should have been added
        for section in LOCKED_SECTIONS:
            assert section in partial_prompts


# =============================================================
# UNIT TESTS — Frontmatter Stripping
# =============================================================


class TestStripFrontmatter:
    """Test YAML frontmatter removal."""

    def test_strips_frontmatter(self, worker: PromptWorker) -> None:
        """Verify frontmatter is removed from content."""
        content = "---\nname: test\ndescription: test\n---\n\n# Actual Content\nBody text."
        result = worker._strip_frontmatter(content)
        assert result.strip().startswith("# Actual Content")
        assert "name: test" not in result

    def test_no_frontmatter_unchanged(self, worker: PromptWorker) -> None:
        """Verify content without frontmatter is returned unchanged."""
        content = "# Just a heading\nSome body text."
        result = worker._strip_frontmatter(content)
        assert result == content


# =============================================================
# UNIT TESTS — User Message Building
# =============================================================


class TestBuildUserMessage:
    """Test user message construction."""

    def test_basic_message(self, worker: PromptWorker, sample_job: Job) -> None:
        """Verify basic message includes theme and event."""
        message = worker._build_user_message(sample_job)
        assert "Lilo & Stitch" in message
        assert "birthday" in message

    def test_style_hint_included(self, worker: PromptWorker) -> None:
        """Verify style hint is included when provided."""
        job = Job(theme="Bluey", event_type="birthday", style_hint="flat 2D cartoon")
        message = worker._build_user_message(job)
        assert "flat 2D cartoon" in message

    def test_count_included(self, worker: PromptWorker) -> None:
        """Verify prompt count is included when provided."""
        job = Job(theme="Minnie Mouse", event_type="birthday", prompt_count=150)
        message = worker._build_user_message(job)
        assert "150" in message


# =============================================================
# INTEGRATION TESTS — Require GOOGLE_API_KEY
# =============================================================


@pytest.mark.integration
class TestPromptWorkerIntegration:
    """Integration tests that call the actual Gemini API."""

    def test_full_prompt_generation(self) -> None:
        """Test full prompt generation with Gemini API."""
        job = Job(
            theme="Lilo & Stitch",
            event_type="birthday",
            prompt_count=30,  # Small count for faster testing
        )

        worker = PromptWorker()
        result = worker.run(job)

        assert result.status != JobStatus.FAILED
        assert result.total_prompt_count > 0
        assert "MAIN_CHARACTER" in result.prompts
        assert len(result.prompts["MAIN_CHARACTER"]) > 0
        assert result.raw_prompt_text is not None
