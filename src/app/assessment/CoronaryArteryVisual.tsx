"use client";

import React from "react";

export default function CoronaryArteryVisual() {
  return (
    <div className="ax-artery-visual" aria-hidden="true">
      <svg viewBox="0 0 1100 140" fill="none" className="ax-artery-svg" preserveAspectRatio="xMidYMid meet">
        <defs>
          {/* Edge fade mask for natural dissolving into ivory background */}
          <linearGradient id="ax-h-mask" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#000" stopOpacity="0" />
            <stop offset="6%" stopColor="#fff" stopOpacity="0.3" />
            <stop offset="14%" stopColor="#fff" stopOpacity="1" />
            <stop offset="86%" stopColor="#fff" stopOpacity="1" />
            <stop offset="94%" stopColor="#fff" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#000" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="ax-v-mask" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#000" stopOpacity="0" />
            <stop offset="10%" stopColor="#fff" stopOpacity="1" />
            <stop offset="90%" stopColor="#fff" stopOpacity="1" />
            <stop offset="100%" stopColor="#000" stopOpacity="0" />
          </linearGradient>
          <mask id="ax-artery-vignette">
            <rect width="1100" height="140" fill="url(#ax-h-mask)" />
            <rect width="1100" height="140" fill="url(#ax-v-mask)" style={{ mixBlendMode: "multiply" }} />
          </mask>
          <linearGradient id="ax-lumen-tint" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#7D0A14" stopOpacity="0.07" />
            <stop offset="25%" stopColor="#7D0A14" stopOpacity="0.025" />
            <stop offset="75%" stopColor="#7D0A14" stopOpacity="0.025" />
            <stop offset="100%" stopColor="#7D0A14" stopOpacity="0.065" />
          </linearGradient>
          <linearGradient id="ax-wall-tint" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#8B0E0E" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#8B0E0E" stopOpacity="0.14" />
          </linearGradient>
        </defs>

        <g mask="url(#ax-artery-vignette)">
          <path d="M 185,54.99 L 195,55.39 L 205,55.79 L 215,56.19 L 225,56.58 L 235,56.97 L 245,57.34 L 255,57.70 L 265,58.05 L 275,58.37 L 285,58.67 L 295,58.95 L 305,59.20 L 315,59.42 L 325,59.61 L 335,59.77 L 345,59.89 L 355,59.98 L 365,60.03 L 375,60.04 L 385,60.01 L 395,59.95 L 405,59.84 L 415,59.70 L 425,59.53 L 435,59.32 L 445,59.07 L 455,58.79 L 465,58.49 L 475,58.15 L 485,57.79 L 495,57.41 L 505,57.01 L 515,56.59 L 525,56.16 L 535,55.73 L 545,55.28 L 555,54.83 L 565,54.38 L 575,53.94 L 585,53.50 L 595,53.08 L 605,52.66 L 615,52.27 L 625,51.89 L 635,51.53 L 645,51.19 L 655,50.88 L 665,50.60 L 675,50.34 L 685,50.11 L 695,49.92 L 705,49.75 L 715,49.62 L 725,49.51 L 735,49.44 L 745,49.39 L 755,49.38 L 765,49.39 L 775,49.43 L 785,49.50 L 795,49.59 L 805,49.71 L 815,49.84 L 825,50.00 L 835,50.17 L 845,50.37 L 855,50.57 L 855,78.09 L 845,78.14 L 835,78.22 L 825,78.33 L 815,78.48 L 805,78.65 L 795,78.86 L 785,79.09 L 775,79.34 L 765,79.62 L 755,79.91 L 745,80.23 L 735,80.56 L 725,80.90 L 715,81.26 L 705,81.63 L 695,82.00 L 685,82.38 L 675,82.76 L 665,83.14 L 655,83.52 L 645,83.90 L 635,84.28 L 625,84.65 L 615,85.01 L 605,85.37 L 595,85.72 L 585,86.06 L 575,86.39 L 565,86.72 L 555,87.03 L 545,87.33 L 535,87.62 L 525,87.90 L 515,88.17 L 505,88.44 L 495,88.69 L 485,88.93 L 475,89.16 L 465,89.39 L 455,89.60 L 445,89.81 L 435,90.01 L 425,90.20 L 415,90.38 L 405,90.55 L 395,90.72 L 385,90.87 L 375,91.02 L 365,91.15 L 355,91.28 L 345,91.39 L 335,91.49 L 325,91.58 L 315,91.65 L 305,91.72 L 295,91.76 L 285,91.79 L 275,91.81 L 265,91.80 L 255,91.78 L 245,91.74 L 235,91.68 L 225,91.60 L 215,91.50 L 205,91.38 L 195,91.23 L 185,91.07 Z" fill="url(#ax-lumen-tint)" />
          <path d="M 190,63.11 L 205,63.62 L 220,64.12 L 235,64.60 L 250,65.06 L 265,65.47 L 280,65.85 L 295,66.17 L 310,66.44 L 325,66.65 L 340,66.79 L 355,66.86 L 370,66.87 L 385,66.80 L 400,66.66 L 415,66.45 L 430,66.18 L 445,65.83 L 460,65.43 L 475,64.97 L 490,64.47 L 505,63.92 L 520,63.35 L 535,62.74 L 550,62.12 L 565,61.50 L 580,60.87 L 595,60.26 L 610,59.66 L 625,59.09 L 640,58.56 L 655,58.06 L 670,57.61 L 685,57.21 L 700,56.87 L 715,56.58 L 730,56.35 L 745,56.18 L 760,56.06 L 775,56.01 L 790,56.02 L 805,56.07 L 820,56.19 L 835,56.35 L 850,56.55" stroke="#8B0E0E" strokeWidth="0.65" strokeDasharray="3 4" strokeOpacity="0.22" fill="none" />
          <path d="M 190,68.86 L 205,69.31 L 220,69.75 L 235,70.16 L 250,70.53 L 265,70.87 L 280,71.17 L 295,71.42 L 310,71.62 L 325,71.76 L 340,71.85 L 355,71.87 L 370,71.84 L 385,71.74 L 400,71.58 L 415,71.36 L 430,71.08 L 445,70.75 L 460,70.37 L 475,69.94 L 490,69.46 L 505,68.95 L 520,68.41 L 535,67.85 L 550,67.26 L 565,66.67 L 580,66.07 L 595,65.48 L 610,64.90 L 625,64.34 L 640,63.80 L 655,63.29 L 670,62.81 L 685,62.37 L 700,61.98 L 715,61.64 L 730,61.35 L 745,61.11 L 760,60.93 L 775,60.80 L 790,60.72 L 805,60.71 L 820,60.74 L 835,60.83 L 850,60.97" stroke="#8B0E0E" strokeWidth="0.65" strokeDasharray="none" strokeOpacity="0.22" fill="none" />
          <path d="M 190,73.18 L 205,73.58 L 220,73.97 L 235,74.32 L 250,74.64 L 265,74.92 L 280,75.16 L 295,75.36 L 310,75.50 L 325,75.60 L 340,75.64 L 355,75.63 L 370,75.56 L 385,75.44 L 400,75.27 L 415,75.04 L 430,74.77 L 445,74.44 L 460,74.07 L 475,73.66 L 490,73.21 L 505,72.72 L 520,72.21 L 535,71.67 L 550,71.12 L 565,70.55 L 580,69.98 L 595,69.40 L 610,68.83 L 625,68.27 L 640,67.72 L 655,67.20 L 670,66.71 L 685,66.25 L 700,65.82 L 715,65.44 L 730,65.10 L 745,64.81 L 760,64.57 L 775,64.39 L 790,64.26 L 805,64.18 L 820,64.16 L 835,64.20 L 850,64.29" stroke="#8B0E0E" strokeWidth="0.65" strokeDasharray="none" strokeOpacity="0.35" fill="none" />
          <path d="M 190,77.49 L 205,77.85 L 220,78.19 L 235,78.49 L 250,78.75 L 265,78.97 L 280,79.16 L 295,79.29 L 310,79.39 L 325,79.43 L 340,79.43 L 355,79.38 L 370,79.29 L 385,79.14 L 400,78.96 L 415,78.72 L 430,78.45 L 445,78.13 L 460,77.77 L 475,77.38 L 490,76.95 L 505,76.49 L 520,76.01 L 535,75.50 L 550,74.97 L 565,74.43 L 580,73.88 L 595,73.32 L 610,72.76 L 625,72.20 L 640,71.65 L 655,71.12 L 670,70.61 L 685,70.12 L 700,69.66 L 715,69.24 L 730,68.85 L 745,68.51 L 760,68.22 L 775,67.97 L 790,67.79 L 805,67.65 L 820,67.58 L 835,67.56 L 850,67.61" stroke="#8B0E0E" strokeWidth="0.65" strokeDasharray="none" strokeOpacity="0.22" fill="none" />
          <path d="M 190,83.24 L 205,83.55 L 220,83.81 L 235,84.04 L 250,84.23 L 265,84.38 L 280,84.48 L 295,84.54 L 310,84.57 L 325,84.55 L 340,84.49 L 355,84.39 L 370,84.25 L 385,84.08 L 400,83.87 L 415,83.63 L 430,83.36 L 445,83.05 L 460,82.71 L 475,82.34 L 490,81.95 L 505,81.52 L 520,81.07 L 535,80.60 L 550,80.11 L 565,79.60 L 580,79.08 L 595,78.54 L 610,77.99 L 625,77.44 L 640,76.89 L 655,76.34 L 670,75.80 L 685,75.28 L 700,74.78 L 715,74.30 L 730,73.85 L 745,73.44 L 760,73.08 L 775,72.76 L 790,72.49 L 805,72.29 L 820,72.14 L 835,72.05 L 850,72.03" stroke="#8B0E0E" strokeWidth="0.65" strokeDasharray="3 4" strokeOpacity="0.22" fill="none" />
          <path d="M 196,55.59 Q 200,61.59 204,55.59" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 196,91.31 Q 200,85.31 204,91.31" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 214,56.31 Q 218,62.31 222,56.31" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 214,91.53 Q 218,85.53 222,91.53" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 232,57.01 Q 236,63.01 240,57.01" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 232,91.68 Q 236,85.68 240,91.68" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 250,57.67 Q 254,63.67 258,57.67" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 250,91.78 Q 254,85.78 258,91.78" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 268,58.28 Q 272,64.28 276,58.28" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 268,91.81 Q 272,85.81 276,91.81" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 286,58.82 Q 290,64.82 294,58.82" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 286,91.78 Q 290,85.78 294,91.78" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 304,59.27 Q 308,65.27 312,59.27" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 304,91.70 Q 308,85.70 312,91.70" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 322,59.63 Q 326,65.63 330,59.63" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 322,91.57 Q 326,85.57 330,91.57" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 340,59.88 Q 344,65.88 348,59.88" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 340,91.40 Q 344,85.40 348,91.40" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 358,60.02 Q 362,66.02 366,60.02" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 358,91.19 Q 362,85.19 366,91.19" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 376,60.03 Q 380,66.03 384,60.03" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 376,90.94 Q 380,84.94 384,90.94" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 394,59.92 Q 398,65.92 402,59.92" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 394,90.67 Q 398,84.67 402,90.67" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 412,59.69 Q 416,65.69 420,59.69" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 412,90.36 Q 416,84.36 420,90.36" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 430,59.34 Q 434,65.34 438,59.34" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 430,90.03 Q 434,84.03 438,90.03" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 448,58.88 Q 452,64.88 456,58.88" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 448,89.67 Q 452,83.67 456,89.67" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 466,58.32 Q 470,64.32 474,58.32" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 466,89.28 Q 470,83.28 474,89.28" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 484,57.68 Q 488,63.68 492,57.68" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 484,88.86 Q 488,82.86 492,88.86" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 502,56.97 Q 506,62.97 510,56.97" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 502,88.41 Q 506,82.41 510,88.41" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 520,56.21 Q 524,62.21 528,56.21" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 520,87.93 Q 524,81.93 528,87.93" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 538,55.41 Q 542,61.41 546,55.41" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 538,87.42 Q 542,81.42 546,87.42" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 556,54.61 Q 560,60.61 564,54.61" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 556,86.87 Q 560,80.87 564,86.87" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 574,53.81 Q 578,59.81 582,53.81" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 574,86.29 Q 578,80.29 582,86.29" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 592,53.04 Q 596,59.04 600,53.04" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 592,85.69 Q 596,79.69 600,85.69" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 610,52.31 Q 614,58.31 618,52.31" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 610,85.05 Q 614,79.05 618,85.05" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 628,51.63 Q 632,57.63 636,51.63" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 628,84.39 Q 632,78.39 636,84.39" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 646,51.03 Q 650,57.03 654,51.03" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 646,83.71 Q 650,77.71 654,83.71" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 664,50.52 Q 668,56.52 672,50.52" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 664,83.03 Q 668,77.03 672,83.03" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 682,50.09 Q 686,56.09 690,50.09" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 682,82.34 Q 686,76.34 690,82.34" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 700,49.77 Q 704,55.77 708,49.77" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 700,81.66 Q 704,75.66 708,81.66" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 718,49.54 Q 722,55.54 726,49.54" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 718,81.01 Q 722,75.01 726,81.01" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 736,49.41 Q 740,55.41 744,49.41" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 736,80.39 Q 740,74.39 744,80.39" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 754,49.38 Q 758,55.38 762,49.38" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 754,79.82 Q 758,73.82 762,79.82" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 772,49.44 Q 776,55.44 780,49.44" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 772,79.31 Q 776,73.31 780,79.31" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 790,49.58 Q 794,55.58 798,49.58" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 790,78.88 Q 794,72.88 798,78.88" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 808,49.80 Q 812,55.80 816,49.80" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 808,78.53 Q 812,72.53 816,78.53" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 826,50.09 Q 830,56.09 834,50.09" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 826,78.27 Q 830,72.27 834,78.27" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 844,50.43 Q 848,56.43 852,50.43" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 844,78.12 Q 848,72.12 852,78.12" stroke="#7D0A14" strokeWidth="0.5" strokeOpacity="0.25" fill="none" />
          <path d="M 25,44.17 Q 31,68.36 25,92.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 36,44.37 Q 42,68.64 36,92.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 47,44.58 Q 53,68.93 47,93.27" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 58,44.82 Q 64,69.22 58,93.63" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 69,45.08 Q 75,69.53 69,93.99" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 80,45.36 Q 86,69.85 80,94.35" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 91,45.67 Q 97,70.18 91,94.70" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 102,45.99 Q 108,70.51 102,95.04" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 113,46.34 Q 119,70.85 113,95.37" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 124,46.70 Q 130,71.19 124,95.68" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 135,47.09 Q 141,71.53 135,95.98" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 146,47.49 Q 152,71.87 146,96.26" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 157,47.90 Q 163,72.21 157,96.52" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 168,48.32 Q 174,72.54 168,96.75" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 179,48.76 Q 185,72.86 179,96.97" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.30" fill="none" />
          <path d="M 860,44.68 Q 865,64.38 860,84.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 871,44.93 Q 876,64.51 871,84.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 882,45.19 Q 887,64.66 882,84.14" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 893,45.46 Q 898,64.84 893,84.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 904,45.73 Q 909,65.05 904,84.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 915,46.02 Q 920,65.27 915,84.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 926,46.30 Q 931,65.52 926,84.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 937,46.60 Q 942,65.79 937,84.99" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 948,46.89 Q 953,66.08 948,85.27" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 959,47.18 Q 964,66.39 959,85.59" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 970,47.47 Q 975,66.71 970,85.94" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 981,47.77 Q 986,67.04 981,86.31" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 992,48.06 Q 997,67.38 992,86.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1003,48.35 Q 1008,67.74 1003,87.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1014,48.63 Q 1019,68.10 1014,87.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1025,48.92 Q 1030,68.46 1025,88.00" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1036,49.20 Q 1041,68.83 1036,88.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1047,49.48 Q 1052,69.19 1047,88.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1058,49.76 Q 1063,69.56 1058,89.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 1069,50.04 Q 1074,69.92 1069,89.81" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.28" fill="none" />
          <path d="M 0,43.80 L 10,43.94 L 20,44.09 L 30,44.26 L 40,44.44 L 50,44.65 L 60,44.87 L 70,45.10 L 80,45.36 L 90,45.64 L 100,45.93 L 110,46.24 L 120,46.57 L 130,46.91 L 140,47.27 L 150,47.63 L 160,48.01 L 170,48.40 L 180,48.79 L 190,49.19 L 200,49.59 L 210,49.99 L 220,50.39 L 230,50.78 L 240,51.16 L 250,51.52 L 260,51.88 L 270,52.21 L 280,52.53 L 290,52.82 L 300,53.08 L 310,53.32 L 320,53.52 L 330,53.70 L 340,53.84 L 350,53.94 L 360,54.01 L 370,54.04 L 380,54.03 L 390,53.98 L 400,53.90 L 410,53.78 L 420,53.62 L 430,53.43 L 440,53.20 L 450,52.94 L 460,52.64 L 470,52.32 L 480,51.98 L 490,51.60 L 500,51.21 L 510,50.80 L 520,50.38 L 530,49.95 L 540,49.50 L 550,49.06 L 560,48.61 L 570,48.16 L 580,47.72 L 590,47.29 L 600,46.87 L 610,46.46 L 620,46.07 L 630,45.70 L 640,45.36 L 650,45.03 L 660,44.74 L 670,44.47 L 680,44.22 L 690,44.01 L 700,43.83 L 710,43.68 L 720,43.56 L 730,43.47 L 740,43.41 L 750,43.38 L 760,43.38 L 770,43.41 L 780,43.46 L 790,43.54 L 800,43.65 L 810,43.77 L 820,43.92 L 830,44.09 L 840,44.27 L 850,44.47 L 860,44.68 L 870,44.90 L 880,45.14 L 890,45.38 L 900,45.63 L 910,45.89 L 920,46.15 L 930,46.41 L 940,46.68 L 950,46.94 L 960,47.21 L 970,47.47 L 980,47.74 L 990,48.00 L 1000,48.27 L 1010,48.53 L 1020,48.79 L 1030,49.04 L 1040,49.30 L 1050,49.56 L 1060,49.81 L 1070,50.06 L 1080,50.31 L 1090,50.56 L 1100,50.81" stroke="#670912" strokeWidth="1.25" strokeOpacity="0.82" fill="none" />
          <path d="M 0,91.80 L 10,92.09 L 20,92.40 L 30,92.72 L 40,93.04 L 50,93.37 L 60,93.69 L 70,94.02 L 80,94.35 L 90,94.66 L 100,94.98 L 110,95.28 L 120,95.57 L 130,95.85 L 140,96.11 L 150,96.35 L 160,96.58 L 170,96.79 L 180,96.98 L 190,97.16 L 200,97.31 L 210,97.44 L 220,97.55 L 230,97.64 L 240,97.71 L 250,97.76 L 260,97.79 L 270,97.81 L 280,97.80 L 290,97.78 L 300,97.74 L 310,97.69 L 320,97.62 L 330,97.54 L 340,97.44 L 350,97.33 L 360,97.21 L 370,97.08 L 380,96.94 L 390,96.80 L 400,96.64 L 410,96.47 L 420,96.29 L 430,96.11 L 440,95.91 L 450,95.71 L 460,95.50 L 470,95.28 L 480,95.05 L 490,94.81 L 500,94.56 L 510,94.31 L 520,94.04 L 530,93.76 L 540,93.48 L 550,93.18 L 560,92.87 L 570,92.56 L 580,92.23 L 590,91.89 L 600,91.55 L 610,91.19 L 620,90.83 L 630,90.46 L 640,90.09 L 650,89.71 L 660,89.33 L 670,88.95 L 680,88.57 L 690,88.19 L 700,87.81 L 710,87.44 L 720,87.08 L 730,86.73 L 740,86.39 L 750,86.07 L 760,85.76 L 770,85.48 L 780,85.21 L 790,84.97 L 800,84.75 L 810,84.56 L 820,84.40 L 830,84.27 L 840,84.18 L 850,84.11 L 860,84.08 L 870,84.09 L 880,84.12 L 890,84.20 L 900,84.31 L 910,84.45 L 920,84.62 L 930,84.83 L 940,85.06 L 950,85.33 L 960,85.62 L 970,85.94 L 980,86.28 L 990,86.64 L 1000,87.01 L 1010,87.40 L 1020,87.80 L 1030,88.21 L 1040,88.62 L 1050,89.03 L 1060,89.44 L 1070,89.85 L 1080,90.24 L 1090,90.63 L 1100,91.00" stroke="#670912" strokeWidth="1.25" strokeOpacity="0.82" fill="none" />
          <path d="M 15,42.61 L 29,42.84 L 43,43.10 L 57,43.40 L 71,43.73 L 85,44.10 L 99,44.50 L 113,44.94 L 127,45.41 L 141,45.90 L 155,46.42 L 169,46.96 L 183,47.51 L 197,48.07 L 211,48.63 L 225,49.18 L 239,49.72 L 253,50.23 L 267,50.71 L 281,51.16 L 295,51.55 L 309,51.89 L 323,52.18 L 337,52.40 L 351,52.55 L 365,52.63 L 379,52.63 L 393,52.56 L 407,52.42 L 421,52.20 L 435,51.92 L 449,51.56 L 463,51.15 L 477,50.68 L 491,50.17 L 505,49.61 L 519,49.02 L 533,48.41 L 547,47.79 L 561,47.16 L 575,46.54 L 589,45.93 L 603,45.35 L 617,44.79 L 631,44.27 L 645,43.79 L 659,43.36 L 673,42.99 L 687,42.67 L 701,42.41 L 715,42.22 L 729,42.08 L 743,42.00 L 757,41.98 L 771,42.01 L 785,42.10 L 799,42.23 L 813,42.41 L 827,42.63 L 841,42.89 L 855,43.17 L 869,43.48 L 883,43.81 L 897,44.16 L 911,44.51 L 925,44.88 L 939,45.25 L 953,45.62 L 967,45.99 L 981,46.37 L 995,46.74 L 1009,47.10 L 1023,47.46 L 1037,47.82 L 1051,48.18 L 1065,48.53 L 1079,48.89" stroke="#8B0E0E" strokeWidth="0.5" strokeDasharray="6 3" strokeOpacity="0.32" fill="none" />
          <path d="M 15,93.65 L 29,94.08 L 43,94.54 L 57,95.00 L 71,95.45 L 85,95.91 L 99,96.35 L 113,96.77 L 127,97.16 L 141,97.53 L 155,97.87 L 169,98.17 L 183,98.44 L 197,98.66 L 211,98.85 L 225,99.00 L 239,99.10 L 253,99.17 L 267,99.20 L 281,99.20 L 295,99.16 L 309,99.09 L 323,99.00 L 337,98.87 L 351,98.72 L 365,98.55 L 379,98.36 L 393,98.15 L 407,97.92 L 421,97.67 L 435,97.41 L 449,97.13 L 463,96.83 L 477,96.52 L 491,96.19 L 505,95.84 L 519,95.47 L 533,95.08 L 547,94.67 L 561,94.24 L 575,93.79 L 589,93.33 L 603,92.84 L 617,92.34 L 631,91.83 L 645,91.30 L 659,90.77 L 673,90.24 L 687,89.70 L 701,89.18 L 715,88.66 L 729,88.16 L 743,87.69 L 757,87.25 L 771,86.85 L 785,86.49 L 799,86.17 L 813,85.91 L 827,85.71 L 841,85.57 L 855,85.49 L 869,85.48 L 883,85.54 L 897,85.67 L 911,85.86 L 925,86.12 L 939,86.44 L 953,86.81 L 967,87.24 L 981,87.71 L 995,88.22 L 1009,88.76 L 1023,89.32 L 1037,89.90 L 1051,90.47 L 1065,91.05 L 1079,91.60" stroke="#8B0E0E" strokeWidth="0.5" strokeDasharray="6 3" strokeOpacity="0.32" fill="none" />
          <path d="M 15,45.41 L 29,45.64 L 43,45.90 L 57,46.20 L 71,46.53 L 85,46.90 L 99,47.30 L 113,47.74 L 127,48.21 L 141,48.70 L 155,49.22 L 169,49.76 L 183,50.31 L 197,50.87 L 211,51.43 L 225,51.98 L 239,52.52 L 253,53.03 L 267,53.51 L 281,53.96 L 295,54.35 L 309,54.69 L 323,54.98 L 337,55.20 L 351,55.35 L 365,55.43 L 379,55.43 L 393,55.36 L 407,55.22 L 421,55.00 L 435,54.72 L 449,54.36 L 463,53.95 L 477,53.48 L 491,52.97 L 505,52.41 L 519,51.82 L 533,51.21 L 547,50.59 L 561,49.96 L 575,49.34 L 589,48.73 L 603,48.15 L 617,47.59 L 631,47.07 L 645,46.59 L 659,46.16 L 673,45.79 L 687,45.47 L 701,45.21 L 715,45.02 L 729,44.88 L 743,44.80 L 757,44.78 L 771,44.81 L 785,44.90 L 799,45.03 L 813,45.21 L 827,45.43 L 841,45.69 L 855,45.97 L 869,46.28 L 883,46.61 L 897,46.96 L 911,47.31 L 925,47.68 L 939,48.05 L 953,48.42 L 967,48.79 L 981,49.17 L 995,49.54 L 1009,49.90 L 1023,50.26 L 1037,50.62 L 1051,50.98 L 1065,51.33 L 1079,51.69" stroke="#8B0E0E" strokeWidth="0.5" strokeDasharray="6 3" strokeOpacity="0.32" fill="none" />
          <path d="M 15,90.85 L 29,91.28 L 43,91.74 L 57,92.20 L 71,92.65 L 85,93.11 L 99,93.55 L 113,93.97 L 127,94.36 L 141,94.73 L 155,95.07 L 169,95.37 L 183,95.64 L 197,95.86 L 211,96.05 L 225,96.20 L 239,96.30 L 253,96.37 L 267,96.40 L 281,96.40 L 295,96.36 L 309,96.29 L 323,96.20 L 337,96.07 L 351,95.92 L 365,95.75 L 379,95.56 L 393,95.35 L 407,95.12 L 421,94.87 L 435,94.61 L 449,94.33 L 463,94.03 L 477,93.72 L 491,93.39 L 505,93.04 L 519,92.67 L 533,92.28 L 547,91.87 L 561,91.44 L 575,90.99 L 589,90.53 L 603,90.04 L 617,89.54 L 631,89.03 L 645,88.50 L 659,87.97 L 673,87.44 L 687,86.90 L 701,86.38 L 715,85.86 L 729,85.36 L 743,84.89 L 757,84.45 L 771,84.05 L 785,83.69 L 799,83.37 L 813,83.11 L 827,82.91 L 841,82.77 L 855,82.69 L 869,82.68 L 883,82.74 L 897,82.87 L 911,83.06 L 925,83.32 L 939,83.64 L 953,84.01 L 967,84.44 L 981,84.91 L 995,85.42 L 1009,85.96 L 1023,86.52 L 1037,87.10 L 1051,87.67 L 1065,88.25 L 1079,88.80" stroke="#8B0E0E" strokeWidth="0.5" strokeDasharray="6 3" strokeOpacity="0.32" fill="none" />
          <path d="M 190,49.19 L 198,49.51 L 206,49.83 L 214,50.15 L 222,50.47 L 230,50.78 L 238,51.08 L 246,51.38 L 254,51.67 L 262,51.95 L 270,52.21 L 278,52.46 L 286,52.70 L 294,52.92 L 302,53.13 L 310,53.32 L 318,53.48 L 326,53.63 L 334,53.76 L 342,53.86 L 350,53.94 L 358,54.00 L 366,54.03 L 374,54.04 L 382,54.02 L 390,53.98 L 398,53.92 L 406,53.83 L 414,53.72 L 422,53.58 L 430,53.43 L 438,53.25 L 446,53.04 L 454,52.82 L 462,52.58 L 470,52.32 L 478,52.05 L 486,51.76 L 494,51.45 L 502,51.13 L 510,50.80 L 518,50.47 L 526,50.12 L 534,49.77 L 542,49.41 L 550,49.06 L 558,48.70 L 566,48.34 L 574,47.99 L 582,47.63 L 590,47.29 L 598,46.95 L 606,46.62 L 614,46.31 L 622,46.00 L 630,45.70 L 638,45.42 L 646,45.16 L 654,44.91 L 662,44.68 L 670,44.47 L 678,44.27 L 686,44.09 L 694,43.94 L 702,43.80 L 710,43.68 L 718,43.58 L 726,43.50 L 734,43.44 L 742,43.40 L 750,43.38 L 758,43.38 L 766,43.39 L 774,43.43 L 782,43.48 L 790,43.54 L 798,43.62 L 806,43.72 L 814,43.83 L 822,43.95 L 830,44.09 L 838,44.23 L 846,44.39 L 854,44.55 L 854,50.55 L 846,50.39 L 838,50.23 L 830,50.09 L 822,49.95 L 814,49.83 L 806,49.72 L 798,49.62 L 790,49.54 L 782,49.48 L 774,49.43 L 766,49.39 L 758,49.38 L 750,49.38 L 742,49.40 L 734,49.44 L 726,49.50 L 718,49.58 L 710,49.68 L 702,49.80 L 694,49.94 L 686,50.09 L 678,50.27 L 670,50.47 L 662,50.68 L 654,50.91 L 646,51.16 L 638,51.42 L 630,51.70 L 622,52.00 L 614,52.31 L 606,52.62 L 598,52.95 L 590,53.29 L 582,53.63 L 574,53.99 L 566,54.34 L 558,54.70 L 550,55.06 L 542,55.41 L 534,55.77 L 526,56.12 L 518,56.47 L 510,56.80 L 502,57.13 L 494,57.45 L 486,57.76 L 478,58.05 L 470,58.32 L 462,58.58 L 454,58.82 L 446,59.04 L 438,59.25 L 430,59.43 L 422,59.58 L 414,59.72 L 406,59.83 L 398,59.92 L 390,59.98 L 382,60.02 L 374,60.04 L 366,60.03 L 358,60.00 L 350,59.94 L 342,59.86 L 334,59.76 L 326,59.63 L 318,59.48 L 310,59.32 L 302,59.13 L 294,58.92 L 286,58.70 L 278,58.46 L 270,58.21 L 262,57.95 L 254,57.67 L 246,57.38 L 238,57.08 L 230,56.78 L 222,56.47 L 214,56.15 L 206,55.83 L 198,55.51 L 190,55.19 Z" fill="url(#ax-wall-tint)" />
          <path d="M 190,91.16 L 198,91.28 L 206,91.39 L 214,91.49 L 222,91.57 L 230,91.64 L 238,91.70 L 246,91.74 L 254,91.78 L 262,91.80 L 270,91.81 L 278,91.80 L 286,91.79 L 294,91.77 L 302,91.73 L 310,91.69 L 318,91.63 L 326,91.57 L 334,91.50 L 342,91.42 L 350,91.33 L 358,91.24 L 366,91.14 L 374,91.03 L 382,90.92 L 390,90.80 L 398,90.67 L 406,90.54 L 414,90.40 L 422,90.25 L 430,90.11 L 438,89.95 L 446,89.79 L 454,89.63 L 462,89.45 L 470,89.28 L 478,89.10 L 486,88.91 L 494,88.71 L 502,88.51 L 510,88.31 L 518,88.09 L 526,87.88 L 534,87.65 L 542,87.42 L 550,87.18 L 558,86.93 L 566,86.68 L 574,86.43 L 582,86.16 L 590,85.89 L 598,85.62 L 606,85.34 L 614,85.05 L 622,84.76 L 630,84.46 L 638,84.17 L 646,83.86 L 654,83.56 L 662,83.26 L 670,82.95 L 678,82.64 L 686,82.34 L 694,82.04 L 702,81.74 L 710,81.44 L 718,81.15 L 726,80.87 L 734,80.59 L 742,80.33 L 750,80.07 L 758,79.82 L 766,79.59 L 774,79.37 L 782,79.16 L 790,78.97 L 798,78.79 L 806,78.64 L 814,78.50 L 822,78.38 L 830,78.27 L 838,78.19 L 846,78.13 L 854,78.10 L 854,84.10 L 846,84.13 L 838,84.19 L 830,84.27 L 822,84.38 L 814,84.50 L 806,84.64 L 798,84.79 L 790,84.97 L 782,85.16 L 774,85.37 L 766,85.59 L 758,85.82 L 750,86.07 L 742,86.33 L 734,86.59 L 726,86.87 L 718,87.15 L 710,87.44 L 702,87.74 L 694,88.04 L 686,88.34 L 678,88.64 L 670,88.95 L 662,89.26 L 654,89.56 L 646,89.86 L 638,90.17 L 630,90.46 L 622,90.76 L 614,91.05 L 606,91.34 L 598,91.62 L 590,91.89 L 582,92.16 L 574,92.43 L 566,92.68 L 558,92.93 L 550,93.18 L 542,93.42 L 534,93.65 L 526,93.88 L 518,94.09 L 510,94.31 L 502,94.51 L 494,94.71 L 486,94.91 L 478,95.10 L 470,95.28 L 462,95.45 L 454,95.63 L 446,95.79 L 438,95.95 L 430,96.11 L 422,96.25 L 414,96.40 L 406,96.54 L 398,96.67 L 390,96.80 L 382,96.92 L 374,97.03 L 366,97.14 L 358,97.24 L 350,97.33 L 342,97.42 L 334,97.50 L 326,97.57 L 318,97.63 L 310,97.69 L 302,97.73 L 294,97.77 L 286,97.79 L 278,97.80 L 270,97.81 L 262,97.80 L 254,97.78 L 246,97.74 L 238,97.70 L 230,97.64 L 222,97.57 L 214,97.49 L 206,97.39 L 198,97.28 L 190,97.16 Z" fill="url(#ax-wall-tint)" />
          <path d="M 190,55.19 L 198,55.51 L 206,55.83 L 214,56.15 L 222,56.47 L 230,56.78 L 238,57.08 L 246,57.38 L 254,57.67 L 262,57.95 L 270,58.21 L 278,58.46 L 286,58.70 L 294,58.92 L 302,59.13 L 310,59.32 L 318,59.48 L 326,59.63 L 334,59.76 L 342,59.86 L 350,59.94 L 358,60.00 L 366,60.03 L 374,60.04 L 382,60.02 L 390,59.98 L 398,59.92 L 406,59.83 L 414,59.72 L 422,59.58 L 430,59.43 L 438,59.25 L 446,59.04 L 454,58.82 L 462,58.58 L 470,58.32 L 478,58.05 L 486,57.76 L 494,57.45 L 502,57.13 L 510,56.80 L 518,56.47 L 526,56.12 L 534,55.77 L 542,55.41 L 550,55.06 L 558,54.70 L 566,54.34 L 574,53.99 L 582,53.63 L 590,53.29 L 598,52.95 L 606,52.62 L 614,52.31 L 622,52.00 L 630,51.70 L 638,51.42 L 646,51.16 L 654,50.91 L 662,50.68 L 670,50.47 L 678,50.27 L 686,50.09 L 694,49.94 L 702,49.80 L 710,49.68 L 718,49.58 L 726,49.50 L 734,49.44 L 742,49.40 L 750,49.38 L 758,49.38 L 766,49.39 L 774,49.43 L 782,49.48 L 790,49.54 L 798,49.62 L 806,49.72 L 814,49.83 L 822,49.95 L 830,50.09 L 838,50.23 L 846,50.39 L 854,50.55" stroke="#7D0A14" strokeWidth="0.85" strokeOpacity="0.80" fill="none" />
          <path d="M 190,91.16 L 198,91.28 L 206,91.39 L 214,91.49 L 222,91.57 L 230,91.64 L 238,91.70 L 246,91.74 L 254,91.78 L 262,91.80 L 270,91.81 L 278,91.80 L 286,91.79 L 294,91.77 L 302,91.73 L 310,91.69 L 318,91.63 L 326,91.57 L 334,91.50 L 342,91.42 L 350,91.33 L 358,91.24 L 366,91.14 L 374,91.03 L 382,90.92 L 390,90.80 L 398,90.67 L 406,90.54 L 414,90.40 L 422,90.25 L 430,90.11 L 438,89.95 L 446,89.79 L 454,89.63 L 462,89.45 L 470,89.28 L 478,89.10 L 486,88.91 L 494,88.71 L 502,88.51 L 510,88.31 L 518,88.09 L 526,87.88 L 534,87.65 L 542,87.42 L 550,87.18 L 558,86.93 L 566,86.68 L 574,86.43 L 582,86.16 L 590,85.89 L 598,85.62 L 606,85.34 L 614,85.05 L 622,84.76 L 630,84.46 L 638,84.17 L 646,83.86 L 654,83.56 L 662,83.26 L 670,82.95 L 678,82.64 L 686,82.34 L 694,82.04 L 702,81.74 L 710,81.44 L 718,81.15 L 726,80.87 L 734,80.59 L 742,80.33 L 750,80.07 L 758,79.82 L 766,79.59 L 774,79.37 L 782,79.16 L 790,78.97 L 798,78.79 L 806,78.64 L 814,78.50 L 822,78.38 L 830,78.27 L 838,78.19 L 846,78.13 L 854,78.10" stroke="#7D0A14" strokeWidth="0.85" strokeOpacity="0.80" fill="none" />
          <line x1="192" y1="49.57" x2="192" y2="54.97" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="192" y1="91.49" x2="192" y2="96.89" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="196" y1="49.73" x2="196" y2="55.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="196" y1="91.55" x2="196" y2="96.95" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="200" y1="49.89" x2="200" y2="55.29" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="200" y1="91.61" x2="200" y2="97.01" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="204" y1="50.05" x2="204" y2="55.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="204" y1="91.66" x2="204" y2="97.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="208" y1="50.21" x2="208" y2="55.61" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="208" y1="91.71" x2="208" y2="97.11" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="212" y1="50.37" x2="212" y2="55.77" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="212" y1="91.76" x2="212" y2="97.16" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="216" y1="50.53" x2="216" y2="55.93" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="216" y1="91.81" x2="216" y2="97.21" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="220" y1="50.69" x2="220" y2="56.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="220" y1="91.85" x2="220" y2="97.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="224" y1="50.84" x2="224" y2="56.24" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="224" y1="91.89" x2="224" y2="97.29" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="228" y1="51.00" x2="228" y2="56.40" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="228" y1="91.92" x2="228" y2="97.32" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="232" y1="51.15" x2="232" y2="56.55" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="232" y1="91.96" x2="232" y2="97.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="236" y1="51.31" x2="236" y2="56.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="236" y1="91.98" x2="236" y2="97.38" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="240" y1="51.46" x2="240" y2="56.86" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="240" y1="92.01" x2="240" y2="97.41" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="244" y1="51.61" x2="244" y2="57.01" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="244" y1="92.03" x2="244" y2="97.43" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="248" y1="51.75" x2="248" y2="57.15" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="248" y1="92.05" x2="248" y2="97.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="252" y1="51.90" x2="252" y2="57.30" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="252" y1="92.07" x2="252" y2="97.47" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="256" y1="52.04" x2="256" y2="57.44" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="256" y1="92.08" x2="256" y2="97.48" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="260" y1="52.18" x2="260" y2="57.58" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="260" y1="92.09" x2="260" y2="97.49" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="264" y1="52.31" x2="264" y2="57.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="264" y1="92.10" x2="264" y2="97.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="268" y1="52.45" x2="268" y2="57.85" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="268" y1="92.10" x2="268" y2="97.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="272" y1="52.58" x2="272" y2="57.98" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="272" y1="92.11" x2="272" y2="97.51" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="276" y1="52.70" x2="276" y2="58.10" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="276" y1="92.10" x2="276" y2="97.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="280" y1="52.83" x2="280" y2="58.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="280" y1="92.10" x2="280" y2="97.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="284" y1="52.94" x2="284" y2="58.34" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="284" y1="92.09" x2="284" y2="97.49" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="288" y1="53.06" x2="288" y2="58.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="288" y1="92.08" x2="288" y2="97.48" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="292" y1="53.17" x2="292" y2="58.57" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="292" y1="92.07" x2="292" y2="97.47" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="296" y1="53.28" x2="296" y2="58.68" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="296" y1="92.06" x2="296" y2="97.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="300" y1="53.38" x2="300" y2="58.78" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="300" y1="92.04" x2="300" y2="97.44" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="304" y1="53.48" x2="304" y2="58.88" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="304" y1="92.02" x2="304" y2="97.42" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="308" y1="53.57" x2="308" y2="58.97" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="308" y1="92.00" x2="308" y2="97.40" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="312" y1="53.66" x2="312" y2="59.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="312" y1="91.97" x2="312" y2="97.37" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="316" y1="53.74" x2="316" y2="59.14" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="316" y1="91.95" x2="316" y2="97.35" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="320" y1="53.82" x2="320" y2="59.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="320" y1="91.92" x2="320" y2="97.32" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="324" y1="53.90" x2="324" y2="59.30" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="324" y1="91.89" x2="324" y2="97.29" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="328" y1="53.96" x2="328" y2="59.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="328" y1="91.85" x2="328" y2="97.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="332" y1="54.03" x2="332" y2="59.43" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="332" y1="91.82" x2="332" y2="97.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="336" y1="54.08" x2="336" y2="59.48" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="336" y1="91.78" x2="336" y2="97.18" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="340" y1="54.14" x2="340" y2="59.54" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="340" y1="91.74" x2="340" y2="97.14" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="344" y1="54.18" x2="344" y2="59.58" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="344" y1="91.70" x2="344" y2="97.10" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="348" y1="54.22" x2="348" y2="59.62" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="348" y1="91.66" x2="348" y2="97.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="352" y1="54.26" x2="352" y2="59.66" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="352" y1="91.61" x2="352" y2="97.01" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="356" y1="54.29" x2="356" y2="59.69" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="356" y1="91.56" x2="356" y2="96.96" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="360" y1="54.31" x2="360" y2="59.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="360" y1="91.51" x2="360" y2="96.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="364" y1="54.32" x2="364" y2="59.72" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="364" y1="91.46" x2="364" y2="96.86" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="368" y1="54.34" x2="368" y2="59.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="368" y1="91.41" x2="368" y2="96.81" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="372" y1="54.34" x2="372" y2="59.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="372" y1="91.36" x2="372" y2="96.76" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="376" y1="54.34" x2="376" y2="59.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="376" y1="91.30" x2="376" y2="96.70" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="380" y1="54.33" x2="380" y2="59.73" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="380" y1="91.24" x2="380" y2="96.64" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="384" y1="54.32" x2="384" y2="59.72" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="384" y1="91.19" x2="384" y2="96.59" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="388" y1="54.30" x2="388" y2="59.70" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="388" y1="91.13" x2="388" y2="96.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="392" y1="54.27" x2="392" y2="59.67" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="392" y1="91.06" x2="392" y2="96.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="396" y1="54.24" x2="396" y2="59.64" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="396" y1="91.00" x2="396" y2="96.40" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="400" y1="54.20" x2="400" y2="59.60" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="400" y1="90.94" x2="400" y2="96.34" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="404" y1="54.16" x2="404" y2="59.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="404" y1="90.87" x2="404" y2="96.27" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="408" y1="54.11" x2="408" y2="59.51" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="408" y1="90.80" x2="408" y2="96.20" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="412" y1="54.05" x2="412" y2="59.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="412" y1="90.73" x2="412" y2="96.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="416" y1="53.99" x2="416" y2="59.39" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="416" y1="90.66" x2="416" y2="96.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="420" y1="53.92" x2="420" y2="59.32" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="420" y1="90.59" x2="420" y2="95.99" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="424" y1="53.85" x2="424" y2="59.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="424" y1="90.52" x2="424" y2="95.92" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="428" y1="53.77" x2="428" y2="59.17" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="428" y1="90.44" x2="428" y2="95.84" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="432" y1="53.68" x2="432" y2="59.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="432" y1="90.37" x2="432" y2="95.77" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="436" y1="53.59" x2="436" y2="58.99" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="436" y1="90.29" x2="436" y2="95.69" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="440" y1="53.50" x2="440" y2="58.90" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="440" y1="90.21" x2="440" y2="95.61" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="444" y1="53.40" x2="444" y2="58.80" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="444" y1="90.13" x2="444" y2="95.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="448" y1="53.29" x2="448" y2="58.69" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="448" y1="90.05" x2="448" y2="95.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="452" y1="53.18" x2="452" y2="58.58" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="452" y1="89.97" x2="452" y2="95.37" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="456" y1="53.06" x2="456" y2="58.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="456" y1="89.88" x2="456" y2="95.28" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="460" y1="52.94" x2="460" y2="58.34" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="460" y1="89.80" x2="460" y2="95.20" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="464" y1="52.82" x2="464" y2="58.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="464" y1="89.71" x2="464" y2="95.11" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="468" y1="52.69" x2="468" y2="58.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="468" y1="89.62" x2="468" y2="95.02" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="472" y1="52.56" x2="472" y2="57.96" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="472" y1="89.53" x2="472" y2="94.93" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="476" y1="52.42" x2="476" y2="57.82" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="476" y1="89.44" x2="476" y2="94.84" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="480" y1="52.28" x2="480" y2="57.68" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="480" y1="89.35" x2="480" y2="94.75" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="484" y1="52.13" x2="484" y2="57.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="484" y1="89.25" x2="484" y2="94.65" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="488" y1="51.98" x2="488" y2="57.38" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="488" y1="89.16" x2="488" y2="94.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="492" y1="51.83" x2="492" y2="57.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="492" y1="89.06" x2="492" y2="94.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="496" y1="51.67" x2="496" y2="57.07" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="496" y1="88.96" x2="496" y2="94.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="500" y1="51.51" x2="500" y2="56.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="500" y1="88.86" x2="500" y2="94.26" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="504" y1="51.35" x2="504" y2="56.75" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="504" y1="88.76" x2="504" y2="94.16" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="508" y1="51.19" x2="508" y2="56.59" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="508" y1="88.66" x2="508" y2="94.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="512" y1="51.02" x2="512" y2="56.42" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="512" y1="88.55" x2="512" y2="93.95" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="516" y1="50.85" x2="516" y2="56.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="516" y1="88.45" x2="516" y2="93.85" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="520" y1="50.68" x2="520" y2="56.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="520" y1="88.34" x2="520" y2="93.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="524" y1="50.51" x2="524" y2="55.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="524" y1="88.23" x2="524" y2="93.63" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="528" y1="50.33" x2="528" y2="55.73" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="528" y1="88.12" x2="528" y2="93.52" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="532" y1="50.16" x2="532" y2="55.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="532" y1="88.01" x2="532" y2="93.41" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="536" y1="49.98" x2="536" y2="55.38" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="536" y1="87.89" x2="536" y2="93.29" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="540" y1="49.80" x2="540" y2="55.20" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="540" y1="87.78" x2="540" y2="93.18" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="544" y1="49.63" x2="544" y2="55.03" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="544" y1="87.66" x2="544" y2="93.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="548" y1="49.45" x2="548" y2="54.85" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="548" y1="87.54" x2="548" y2="92.94" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="552" y1="49.27" x2="552" y2="54.67" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="552" y1="87.42" x2="552" y2="92.82" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="556" y1="49.09" x2="556" y2="54.49" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="556" y1="87.30" x2="556" y2="92.70" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="560" y1="48.91" x2="560" y2="54.31" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="560" y1="87.17" x2="560" y2="92.57" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="564" y1="48.73" x2="564" y2="54.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="564" y1="87.05" x2="564" y2="92.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="568" y1="48.55" x2="568" y2="53.95" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="568" y1="86.92" x2="568" y2="92.32" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="572" y1="48.37" x2="572" y2="53.77" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="572" y1="86.79" x2="572" y2="92.19" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="576" y1="48.20" x2="576" y2="53.60" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="576" y1="86.66" x2="576" y2="92.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="580" y1="48.02" x2="580" y2="53.42" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="580" y1="86.53" x2="580" y2="91.93" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="584" y1="47.85" x2="584" y2="53.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="584" y1="86.40" x2="584" y2="91.80" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="588" y1="47.68" x2="588" y2="53.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="588" y1="86.26" x2="588" y2="91.66" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="592" y1="47.50" x2="592" y2="52.90" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="592" y1="86.12" x2="592" y2="91.52" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="596" y1="47.34" x2="596" y2="52.74" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="596" y1="85.99" x2="596" y2="91.39" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="600" y1="47.17" x2="600" y2="52.57" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="600" y1="85.85" x2="600" y2="91.25" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="604" y1="47.00" x2="604" y2="52.40" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="604" y1="85.71" x2="604" y2="91.11" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="608" y1="46.84" x2="608" y2="52.24" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="608" y1="85.56" x2="608" y2="90.96" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="612" y1="46.68" x2="612" y2="52.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="612" y1="85.42" x2="612" y2="90.82" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="616" y1="46.53" x2="616" y2="51.93" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="616" y1="85.28" x2="616" y2="90.68" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="620" y1="46.37" x2="620" y2="51.77" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="620" y1="85.13" x2="620" y2="90.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="624" y1="46.22" x2="624" y2="51.62" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="624" y1="84.99" x2="624" y2="90.39" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="628" y1="46.08" x2="628" y2="51.48" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="628" y1="84.84" x2="628" y2="90.24" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="632" y1="45.93" x2="632" y2="51.33" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="632" y1="84.69" x2="632" y2="90.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="636" y1="45.79" x2="636" y2="51.19" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="636" y1="84.54" x2="636" y2="89.94" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="640" y1="45.66" x2="640" y2="51.06" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="640" y1="84.39" x2="640" y2="89.79" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="644" y1="45.52" x2="644" y2="50.92" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="644" y1="84.24" x2="644" y2="89.64" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="648" y1="45.40" x2="648" y2="50.80" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="648" y1="84.09" x2="648" y2="89.49" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="652" y1="45.27" x2="652" y2="50.67" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="652" y1="83.94" x2="652" y2="89.34" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="656" y1="45.15" x2="656" y2="50.55" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="656" y1="83.78" x2="656" y2="89.18" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="660" y1="45.04" x2="660" y2="50.44" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="660" y1="83.63" x2="660" y2="89.03" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="664" y1="44.92" x2="664" y2="50.32" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="664" y1="83.48" x2="664" y2="88.88" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="668" y1="44.82" x2="668" y2="50.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="668" y1="83.33" x2="668" y2="88.73" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="672" y1="44.72" x2="672" y2="50.12" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="672" y1="83.17" x2="672" y2="88.57" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="676" y1="44.62" x2="676" y2="50.02" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="676" y1="83.02" x2="676" y2="88.42" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="680" y1="44.52" x2="680" y2="49.92" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="680" y1="82.87" x2="680" y2="88.27" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="684" y1="44.44" x2="684" y2="49.84" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="684" y1="82.72" x2="684" y2="88.12" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="688" y1="44.35" x2="688" y2="49.75" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="688" y1="82.56" x2="688" y2="87.96" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="692" y1="44.27" x2="692" y2="49.67" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="692" y1="82.41" x2="692" y2="87.81" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="696" y1="44.20" x2="696" y2="49.60" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="696" y1="82.26" x2="696" y2="87.66" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="700" y1="44.13" x2="700" y2="49.53" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="700" y1="82.11" x2="700" y2="87.51" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="704" y1="44.07" x2="704" y2="49.47" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="704" y1="81.96" x2="704" y2="87.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="708" y1="44.01" x2="708" y2="49.41" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="708" y1="81.82" x2="708" y2="87.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="712" y1="43.95" x2="712" y2="49.35" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="712" y1="81.67" x2="712" y2="87.07" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="716" y1="43.90" x2="716" y2="49.30" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="716" y1="81.52" x2="716" y2="86.92" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="720" y1="43.86" x2="720" y2="49.26" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="720" y1="81.38" x2="720" y2="86.78" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="724" y1="43.82" x2="724" y2="49.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="724" y1="81.24" x2="724" y2="86.64" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="728" y1="43.78" x2="728" y2="49.18" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="728" y1="81.10" x2="728" y2="86.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="732" y1="43.75" x2="732" y2="49.15" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="732" y1="80.96" x2="732" y2="86.36" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="736" y1="43.73" x2="736" y2="49.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="736" y1="80.83" x2="736" y2="86.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="740" y1="43.71" x2="740" y2="49.11" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="740" y1="80.69" x2="740" y2="86.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="744" y1="43.69" x2="744" y2="49.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="744" y1="80.56" x2="744" y2="85.96" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="748" y1="43.68" x2="748" y2="49.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="748" y1="80.43" x2="748" y2="85.83" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="752" y1="43.68" x2="752" y2="49.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="752" y1="80.31" x2="752" y2="85.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="756" y1="43.68" x2="756" y2="49.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="756" y1="80.18" x2="756" y2="85.58" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="760" y1="43.68" x2="760" y2="49.08" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="760" y1="80.06" x2="760" y2="85.46" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="764" y1="43.69" x2="764" y2="49.09" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="764" y1="79.94" x2="764" y2="85.34" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="768" y1="43.70" x2="768" y2="49.10" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="768" y1="79.83" x2="768" y2="85.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="772" y1="43.72" x2="772" y2="49.12" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="772" y1="79.72" x2="772" y2="85.12" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="776" y1="43.74" x2="776" y2="49.14" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="776" y1="79.61" x2="776" y2="85.01" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="780" y1="43.76" x2="780" y2="49.16" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="780" y1="79.51" x2="780" y2="84.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="784" y1="43.79" x2="784" y2="49.19" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="784" y1="79.41" x2="784" y2="84.81" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="788" y1="43.82" x2="788" y2="49.22" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="788" y1="79.31" x2="788" y2="84.71" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="792" y1="43.86" x2="792" y2="49.26" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="792" y1="79.22" x2="792" y2="84.62" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="796" y1="43.90" x2="796" y2="49.30" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="796" y1="79.14" x2="796" y2="84.54" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="800" y1="43.95" x2="800" y2="49.35" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="800" y1="79.05" x2="800" y2="84.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="804" y1="43.99" x2="804" y2="49.39" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="804" y1="78.97" x2="804" y2="84.37" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="808" y1="44.05" x2="808" y2="49.45" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="808" y1="78.90" x2="808" y2="84.30" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="812" y1="44.10" x2="812" y2="49.50" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="812" y1="78.83" x2="812" y2="84.23" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="816" y1="44.16" x2="816" y2="49.56" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="816" y1="78.76" x2="816" y2="84.16" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="820" y1="44.22" x2="820" y2="49.62" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="820" y1="78.70" x2="820" y2="84.10" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="824" y1="44.28" x2="824" y2="49.68" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="824" y1="78.65" x2="824" y2="84.05" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="828" y1="44.35" x2="828" y2="49.75" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="828" y1="78.60" x2="828" y2="84.00" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="832" y1="44.42" x2="832" y2="49.82" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="832" y1="78.55" x2="832" y2="83.95" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="836" y1="44.49" x2="836" y2="49.89" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="836" y1="78.51" x2="836" y2="83.91" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="840" y1="44.57" x2="840" y2="49.97" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="840" y1="78.48" x2="840" y2="83.88" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="844" y1="44.65" x2="844" y2="50.05" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="844" y1="78.45" x2="844" y2="83.85" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="848" y1="44.73" x2="848" y2="50.13" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="848" y1="78.42" x2="848" y2="83.82" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="852" y1="44.81" x2="852" y2="50.21" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="852" y1="78.40" x2="852" y2="83.80" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.32" />
          <line x1="856" y1="44.89" x2="856" y2="50.29" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <line x1="856" y1="78.39" x2="856" y2="83.79" stroke="#7D0A14" strokeWidth="0.55" strokeOpacity="0.52" />
          <path d="M 178,48.99 C 182,50.99 186,54.99 190,54.99" stroke="#670912" strokeWidth="0.9" strokeOpacity="0.75" fill="none" />
          <path d="M 178,97.07 C 182,95.07 186,91.07 190,91.07" stroke="#670912" strokeWidth="0.9" strokeOpacity="0.75" fill="none" />
          <path d="M 856,50.68 C 860,46.68 864,44.68 868,44.68" stroke="#670912" strokeWidth="0.9" strokeOpacity="0.75" fill="none" />
          <path d="M 856,78.08 C 860,82.08 864,84.08 868,84.08" stroke="#670912" strokeWidth="0.9" strokeOpacity="0.75" fill="none" />
          <path d="M 358,45 C 365,34 378,24 398,17" stroke="#7D0A14" strokeWidth="1.05" strokeLinecap="round" strokeOpacity="0.82" fill="none" />
          <path d="M 398,17 C 408,13 421,10 436,8" stroke="#7D0A14" strokeWidth="0.65" strokeLinecap="round" strokeOpacity="0.65" fill="none" />
          <path d="M 436,8 C 447,6 458,6 468,5" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.45" fill="none" />
          <path d="M 398,17 C 402,11 410,7 418,5" stroke="#7D0A14" strokeWidth="0.65" strokeLinecap="round" strokeOpacity="0.62" fill="none" />
          <path d="M 418,5 C 424,3 430,3 437,2" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.42" fill="none" />
          <path d="M 452,7 C 457,5 463,4 468,3" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.4" fill="none" />
          <path d="M 382,23 C 388,17 394,14 402,11" stroke="#7D0A14" strokeWidth="0.5" strokeLinecap="round" strokeOpacity="0.5" fill="none" />
          <path d="M 700,44 C 708,35 720,27 738,20" stroke="#7D0A14" strokeWidth="1.0" strokeLinecap="round" strokeOpacity="0.8" fill="none" />
          <path d="M 738,20 C 751,15 766,12 782,9" stroke="#7D0A14" strokeWidth="0.65" strokeLinecap="round" strokeOpacity="0.62" fill="none" />
          <path d="M 782,9 C 794,7 806,7 818,6" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.42" fill="none" />
          <path d="M 738,20 C 744,14 751,10 760,8" stroke="#7D0A14" strokeWidth="0.6" strokeLinecap="round" strokeOpacity="0.58" fill="none" />
          <path d="M 760,8 C 767,5 775,4 783,3" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.4" fill="none" />
          <path d="M 719,30 C 725,23 732,19 740,16" stroke="#7D0A14" strokeWidth="0.5" strokeLinecap="round" strokeOpacity="0.48" fill="none" />
          <path d="M 770,10 C 776,8 782,7 789,6" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.4" fill="none" />
          <path d="M 294,97 C 300,108 311,118 328,125" stroke="#7D0A14" strokeWidth="1.05" strokeLinecap="round" strokeOpacity="0.82" fill="none" />
          <path d="M 328,125 C 340,130 353,133 368,135" stroke="#7D0A14" strokeWidth="0.65" strokeLinecap="round" strokeOpacity="0.65" fill="none" />
          <path d="M 368,135 C 379,136 390,137 401,137" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.42" fill="none" />
          <path d="M 328,125 C 332,130 339,134 347,137" stroke="#7D0A14" strokeWidth="0.6" strokeLinecap="round" strokeOpacity="0.58" fill="none" />
          <path d="M 309,114 C 315,121 322,126 331,130" stroke="#7D0A14" strokeWidth="0.5" strokeLinecap="round" strokeOpacity="0.48" fill="none" />
          <path d="M 351,134 C 356,137 362,138 369,139" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.4" fill="none" />
          <path d="M 648,93 C 655,104 667,114 684,121" stroke="#7D0A14" strokeWidth="1.0" strokeLinecap="round" strokeOpacity="0.8" fill="none" />
          <path d="M 684,121 C 697,126 712,130 729,133" stroke="#7D0A14" strokeWidth="0.65" strokeLinecap="round" strokeOpacity="0.62" fill="none" />
          <path d="M 729,133 C 740,135 751,136 762,136" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.42" fill="none" />
          <path d="M 684,121 C 690,127 697,131 706,135" stroke="#7D0A14" strokeWidth="0.6" strokeLinecap="round" strokeOpacity="0.58" fill="none" />
          <path d="M 666,112 C 672,119 679,124 688,128" stroke="#7D0A14" strokeWidth="0.5" strokeLinecap="round" strokeOpacity="0.48" fill="none" />
          <path d="M 714,131 C 720,134 727,136 734,137" stroke="#7D0A14" strokeWidth="0.42" strokeLinecap="round" strokeOpacity="0.4" fill="none" />
          <path d="M 75,45 C 86,41 98,41 108,46 C 116,50 125,49 135,44" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 98,41 C 103,37 110,36 117,38" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 85,98 C 96,101 107,101 117,97 C 126,93 136,95 145,99" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 107,101 C 113,105 120,106 127,104" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 900,44 C 911,40 924,41 935,46 C 944,50 955,48 966,43" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 924,41 C 930,36 937,35 944,37" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 905,88 C 917,91 928,90 939,86 C 948,82 959,84 970,89" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
          <path d="M 928,90 C 935,95 942,96 950,93" stroke="#8B0E0E" strokeWidth="0.5" strokeOpacity="0.35" fill="none" />
        </g>
      </svg>
    </div>
  );
}
