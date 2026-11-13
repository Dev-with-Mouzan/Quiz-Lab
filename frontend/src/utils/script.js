// Arabic-script characters (Urdu, Arabic, Persian): the ranges used by Urdu text.
const ARABIC_SCRIPT = /[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]/

// Returns the Urdu font class when text contains Arabic-script characters, else ''.
// Used on question and option text so Urdu shows in Jameel Noori Nastaleeq.
export function urduClass(text) {
  return ARABIC_SCRIPT.test(text || '') ? 'urdu-text' : ''
}
