# E3: consistency per profile

## A. Criteria of the representation

U6 columns count logical messages; U4 counts logical messages with any endpoint disagreement.

| Output | Profile | Structural ok | Tasks | Logical msgs | U6 correct | of which multicast | U6 absent | U6 incoherent | U6 no message events | U4 findings |
|---|---|---|---|---|---|---|---|---|---|---|
| artificial1_cl | collaboration | yes | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 |
| artificial1_chl | choreography | yes | 200 | 200 | 0 | 0 | 0 | 0 | 200 | 0 |
| artificial1_complete | complete | yes | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 |
| artificial5_cl | collaboration | yes | 530 | 530 | 486 | 0 | 44 | 0 | 0 | 0 |
| artificial5_chl | choreography | yes | 530 | 530 | 0 | 0 | 0 | 0 | 530 | 0 |
| artificial5_complete | complete | yes | 530 | 530 | 486 | 0 | 44 | 0 | 0 | 0 |
| bpic2013_cl | collaboration | yes | 4051 | 4051 | 4051 | 0 | 0 | 0 | 0 | 0 |
| beanstalk_attack | hierarchical choreography | yes | 489 | 703 | 0 | 0 | 0 | 0 | 703 | 0 |
| 0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d_uniqueFunction | hierarchical choreography | yes | 18 | 21 | 0 | 0 | 0 | 0 | 21 | 0 |
| 0x06012c8cf97bead5deae237070f9587f8e7a266d_uniqueFunction | hierarchical choreography | yes | 204 | 302 | 0 | 0 | 0 | 0 | 302 | 0 |
| 0xb1690c08e213a35ed9bab7b318de14420fb57d8c_uniqueFunction | hierarchical choreography | yes | 6 | 10 | 0 | 0 | 0 | 0 | 10 | 0 |
| 0x00000000219ab540356cbb839cbe05303d7705fa_uniqueFunction | hierarchical choreography | yes | 9 | 17 | 0 | 0 | 0 | 0 | 17 | 0 |
| 0x323a76393544d5ecca80cd6ef2a560c6a395b7e3_uniqueFunction | hierarchical choreography | yes | 21 | 31 | 0 | 0 | 0 | 0 | 31 | 0 |
| 0x9c8ff314c9bc7f6e59a9d9225fb22946427edc03_uniqueFunction | hierarchical choreography | yes | 12 | 13 | 0 | 0 | 0 | 0 | 13 | 0 |
| 0x556b9306565093c855aea9ae92a594704c2cd59e_uniqueFunction | hierarchical choreography | yes | 241 | 361 | 0 | 0 | 0 | 0 | 361 | 0 |
| 0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f_uniqueFunction | hierarchical choreography | yes | 267 | 415 | 0 | 0 | 0 | 0 | 415 | 0 |
| 0x5e_cd49912 | hierarchical choreography | yes | 4 | 5 | 0 | 0 | 0 | 0 | 5 | 0 |
| 0x5efda50f22d34f262c29268506c5fa42cb56a1ce_uniqueFunction | hierarchical choreography | yes | 35 | 47 | 0 | 0 | 0 | 0 | 47 | 0 |
| 0xd90e2f925da726b50c4ed8d0fb90ad053324f31b_uniqueFunction | hierarchical choreography | yes | 85 | 146 | 0 | 0 | 0 | 0 | 146 | 0 |
| 0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc_uniqueFunction | hierarchical choreography | yes | 61 | 88 | 0 | 0 | 0 | 0 | 88 | 0 |
| healthcare_cl | collaboration | yes | 550 | 550 | 524 | 0 | 26 | 0 | 0 | 0 |
| healthcare_chl | choreography | yes | 550 | 550 | 0 | 0 | 0 | 0 | 550 | 0 |
| healthcare_complete | complete | yes | 550 | 550 | 524 | 0 | 26 | 0 | 0 | 0 |
| healthcare_hobeck | collaboration | yes | 116 | 116 | 107 | 0 | 9 | 0 | 0 | 0 |
| real1_cl | collaboration | yes | 44 | 44 | 44 | 0 | 0 | 0 | 0 | 0 |
| real1_chl | choreography | yes | 44 | 44 | 0 | 0 | 0 | 0 | 44 | 0 |
| real1_complete | complete | yes | 44 | 44 | 44 | 0 | 0 | 0 | 0 | 0 |
| real1_hobeck | collaboration | yes | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| real2_cl | collaboration | yes | 869 | 500 | 401 | 0 | 0 | 99 | 0 | 0 |
| real2_chl | choreography | yes | 869 | 500 | 0 | 0 | 0 | 99 | 401 | 0 |
| real2_complete | complete | yes | 869 | 500 | 401 | 0 | 0 | 99 | 0 | 0 |
| real2_hobeck | collaboration | yes | 842 | 480 | 385 | 0 | 0 | 95 | 0 | 0 |
| real3_cl | collaboration | yes | 653 | 492 | 401 | 0 | 13 | 78 | 0 | 0 |
| real3_chl | choreography | yes | 653 | 492 | 0 | 0 | 0 | 78 | 414 | 0 |
| real3_complete | complete | yes | 653 | 492 | 401 | 0 | 13 | 78 | 0 | 0 |
| real3_hobeck | collaboration | yes | 472 | 321 | 240 | 0 | 8 | 73 | 0 | 0 |
| real4_cl | collaboration | yes | 400 | 400 | 400 | 0 | 0 | 0 | 0 | 0 |
| real4_chl | choreography | yes | 400 | 400 | 0 | 0 | 0 | 0 | 400 | 0 |
| real4_complete | complete | yes | 400 | 400 | 400 | 0 | 0 | 0 | 0 | 0 |
| real4_hobeck | collaboration | yes | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| real5_cl | collaboration | yes | 345 | 345 | 345 | 0 | 0 | 0 | 0 | 0 |
| real5_chl | choreography | yes | 345 | 345 | 0 | 0 | 0 | 0 | 345 | 0 |
| real5_complete | complete | yes | 345 | 345 | 345 | 0 | 0 | 0 | 0 | 0 |
| real5_hobeck | collaboration | yes | 15 | 15 | 15 | 0 | 0 | 0 | 0 | 0 |
| smartagriculture_cl | collaboration | yes | 114 | 102 | 95 | 9 | 2 | 5 | 0 | 0 |
| smartagriculture_chl | choreography | yes | 114 | 100 | 0 | 0 | 0 | 5 | 95 | 0 |
| smartagriculture_complete | complete | yes | 114 | 102 | 95 | 9 | 2 | 5 | 0 | 0 |
| smartagriculture_hobeck | collaboration | yes | 114 | 102 | 95 | 9 | 2 | 5 | 0 | 0 |

## B. C0–C16 (ocelchorvalidator) on the export eta_H (violations/checked)

| Output | Profile | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 | C15 | C16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| artificial1_cl | collaboration | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/0 | 0/0 | 0/0 | 0/100 | 0/0 |
| artificial1_chl | choreography | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/0 | 0/0 | 0/0 | 0/100 | 0/0 |
| artificial1_complete | complete | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/200 | 0/0 | 0/0 | 0/0 | 0/100 | 0/0 |
| artificial5_cl | collaboration | 0/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/0 | 0/0 | 0/0 | 136/430 | 0/0 |
| artificial5_chl | choreography | 0/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/0 | 0/0 | 0/0 | 136/430 | 0/0 |
| artificial5_complete | complete | 0/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 44/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/530 | 0/0 | 0/0 | 0/0 | 136/430 | 0/0 |
| bpic2013_cl | collaboration | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/4051 | 0/0 | 0/0 | 0/0 | 15/2069 | 0/0 |
| beanstalk_attack | hierarchical choreography | 0/489 | 0/703 | 0/489 | 1/489 | 0/489 | 0/703 | 1/703 | 0/489 | 0/489 | 0/703 | 0/703 | 0/489 | 0/139 | 0/139 | 0/139 | 1/486 | 0/139 |
| 0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d_uniqueFunction | hierarchical choreography | 0/18 | 0/21 | 0/18 | 0/18 | 0/18 | 0/21 | 0/21 | 0/18 | 0/18 | 0/21 | 0/21 | 0/18 | 0/5 | 0/5 | 0/5 | 0/9 | 0/5 |
| 0x06012c8cf97bead5deae237070f9587f8e7a266d_uniqueFunction | hierarchical choreography | 0/204 | 0/302 | 0/204 | 0/204 | 2/204 | 0/302 | 0/302 | 0/204 | 0/204 | 0/302 | 0/302 | 0/204 | 0/59 | 0/59 | 0/59 | 0/182 | 0/59 |
| 0xb1690c08e213a35ed9bab7b318de14420fb57d8c_uniqueFunction | hierarchical choreography | 0/6 | 0/10 | 0/6 | 0/6 | 0/6 | 0/10 | 0/10 | 0/6 | 0/6 | 0/10 | 0/10 | 0/6 | 0/2 | 0/2 | 0/2 | 0/4 | 0/2 |
| 0x00000000219ab540356cbb839cbe05303d7705fa_uniqueFunction | hierarchical choreography | 0/9 | 0/17 | 0/9 | 0/9 | 0/9 | 0/17 | 0/17 | 0/9 | 0/9 | 0/17 | 0/17 | 0/9 | 0/1 | 0/1 | 0/1 | 0/8 | 0/1 |
| 0x323a76393544d5ecca80cd6ef2a560c6a395b7e3_uniqueFunction | hierarchical choreography | 0/21 | 0/31 | 0/21 | 0/21 | 0/21 | 0/31 | 0/31 | 0/21 | 0/21 | 0/31 | 0/31 | 0/21 | 0/6 | 0/6 | 0/6 | 0/12 | 0/6 |
| 0x9c8ff314c9bc7f6e59a9d9225fb22946427edc03_uniqueFunction | hierarchical choreography | 0/12 | 0/13 | 0/12 | 0/12 | 0/12 | 0/13 | 0/13 | 0/12 | 0/12 | 0/13 | 0/13 | 0/12 | 0/3 | 0/3 | 0/3 | 0/5 | 0/3 |
| 0x556b9306565093c855aea9ae92a594704c2cd59e_uniqueFunction | hierarchical choreography | 0/241 | 0/361 | 0/241 | 0/241 | 10/241 | 0/361 | 0/361 | 0/241 | 0/241 | 0/361 | 0/361 | 0/241 | 0/64 | 0/64 | 0/64 | 0/228 | 0/64 |
| 0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f_uniqueFunction | hierarchical choreography | 0/267 | 0/415 | 0/267 | 0/267 | 0/267 | 0/415 | 0/415 | 0/267 | 0/267 | 0/415 | 0/415 | 0/267 | 0/67 | 0/67 | 0/67 | 0/248 | 0/67 |
| 0x5e_cd49912 | hierarchical choreography | 0/4 | 0/5 | 0/4 | 0/4 | 0/4 | 0/5 | 0/5 | 0/4 | 0/4 | 0/5 | 0/5 | 0/4 | 0/2 | 0/2 | 0/2 | 0/3 | 0/2 |
| 0x5efda50f22d34f262c29268506c5fa42cb56a1ce_uniqueFunction | hierarchical choreography | 0/35 | 0/47 | 0/35 | 0/35 | 0/35 | 0/47 | 0/47 | 0/35 | 0/35 | 0/47 | 0/47 | 0/35 | 0/17 | 0/17 | 0/17 | 0/24 | 0/17 |
| 0xd90e2f925da726b50c4ed8d0fb90ad053324f31b_uniqueFunction | hierarchical choreography | 0/85 | 0/146 | 0/85 | 0/85 | 0/85 | 0/146 | 0/146 | 0/85 | 0/85 | 0/146 | 0/146 | 0/85 | 0/13 | 0/13 | 0/13 | 0/83 | 0/13 |
| 0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc_uniqueFunction | hierarchical choreography | 0/61 | 0/88 | 0/61 | 0/61 | 0/61 | 0/88 | 0/88 | 0/61 | 0/61 | 0/88 | 0/88 | 0/61 | 0/17 | 0/17 | 0/17 | 0/55 | 0/17 |
| healthcare_cl | collaboration | 0/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/0 | 0/0 | 0/0 | 26/450 | 0/0 |
| healthcare_chl | choreography | 0/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/0 | 0/0 | 0/0 | 26/450 | 0/0 |
| healthcare_complete | complete | 0/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 26/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/550 | 0/0 | 0/0 | 0/0 | 26/450 | 0/0 |
| healthcare_hobeck | collaboration | 0/116 | 0/116 | 0/116 | 9/116 | 0/116 | 0/116 | 9/116 | 0/116 | 0/116 | 0/116 | 0/116 | 0/116 | 0/0 | 0/0 | 0/0 | 9/99 | 0/0 |
| real1_cl | collaboration | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/0 | 0/0 | 0/0 | 0/22 | 0/0 |
| real1_chl | choreography | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/0 | 0/0 | 0/0 | 0/22 | 0/0 |
| real1_complete | complete | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/44 | 0/0 | 0/0 | 0/0 | 0/22 | 0/0 |
| real1_hobeck | collaboration | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |
| real2_cl | collaboration | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/0 | 0/0 | 0/0 | 0/769 | 0/0 |
| real2_chl | choreography | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/0 | 0/0 | 0/0 | 0/769 | 0/0 |
| real2_complete | complete | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/869 | 0/0 | 0/0 | 0/0 | 0/769 | 0/0 |
| real2_hobeck | collaboration | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/0 | 0/0 | 0/0 | 0/746 | 0/0 |
| real3_cl | collaboration | 0/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/0 | 0/0 | 0/0 | 119/553 | 0/0 |
| real3_chl | choreography | 0/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/0 | 0/0 | 0/0 | 119/553 | 0/0 |
| real3_complete | complete | 0/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 13/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/653 | 0/0 | 0/0 | 0/0 | 119/553 | 0/0 |
| real3_hobeck | collaboration | 0/472 | 0/472 | 0/472 | 8/472 | 0/472 | 0/472 | 8/472 | 0/472 | 0/472 | 0/472 | 0/472 | 0/472 | 0/0 | 0/0 | 0/0 | 99/413 | 0/0 |
| real4_cl | collaboration | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/0 | 0/0 | 0/0 | 0/300 | 0/0 |
| real4_chl | choreography | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/0 | 0/0 | 0/0 | 0/300 | 0/0 |
| real4_complete | complete | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/400 | 0/0 | 0/0 | 0/0 | 0/300 | 0/0 |
| real4_hobeck | collaboration | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/0 | 0/0 | 0/0 | 0/3 | 0/0 |
| real5_cl | collaboration | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/0 | 0/0 | 0/0 | 0/276 | 0/0 |
| real5_chl | choreography | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/0 | 0/0 | 0/0 | 0/276 | 0/0 |
| real5_complete | complete | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/345 | 0/0 | 0/0 | 0/0 | 0/276 | 0/0 |
| real5_hobeck | collaboration | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/0 | 0/0 | 0/0 | 0/12 | 0/0 |
| smartagriculture_cl | collaboration | 0/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/0 | 0/0 | 0/0 | 9/104 | 0/0 |
| smartagriculture_chl | choreography | 0/114 | 0/114 | 0/114 | 16/114 | 0/114 | 0/114 | 16/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/0 | 0/0 | 0/0 | 9/104 | 0/0 |
| smartagriculture_complete | complete | 0/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/0 | 0/0 | 0/0 | 9/104 | 0/0 |
| smartagriculture_hobeck | collaboration | 0/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/0 | 0/0 | 0/0 | 9/104 | 0/0 |

## C. Cross-check: C0–C16 on Hobeck et al.'s reference OCEL

Same: the reference has the same violation counts as the export of the equivalent unified output (part B).

| Reference of | Same | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 | C15 | C16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| healthcare_hobeck | yes | 0/116 | 0/116 | 0/116 | 9/116 | 0/116 | 0/116 | 9/116 | 0/116 | 0/116 | 0/116 | 0/116 | 0/116 | 0/0 | 0/0 | 0/0 | 9/99 | 0/0 |
| real1_hobeck | yes | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 0/0 | 0/0 | 0/0 | 0/1 | 0/0 |
| real2_hobeck | yes | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/842 | 0/0 | 0/0 | 0/0 | 0/746 | 0/0 |
| real3_hobeck | yes | 0/472 | 0/472 | 0/472 | 8/472 | 0/472 | 0/472 | 8/472 | 0/472 | 0/472 | 0/472 | 0/472 | 0/472 | 0/0 | 0/0 | 0/0 | 99/413 | 0/0 |
| real4_hobeck | yes | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/0 | 0/0 | 0/0 | 0/3 | 0/0 |
| real5_hobeck | yes | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/15 | 0/0 | 0/0 | 0/0 | 0/12 | 0/0 |
| smartagriculture_hobeck | yes | 0/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 28/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/114 | 0/0 | 0/0 | 0/0 | 9/104 | 0/0 |
| beanstalk_attack | yes | 0/489 | 0/703 | 0/489 | 1/489 | 0/489 | 0/703 | 1/703 | 0/489 | 0/489 | 0/703 | 0/703 | 0/489 | 0/139 | 0/139 | 0/139 | 1/486 | 0/139 |
| 0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d_uniqueFunction | yes | 0/18 | 0/21 | 0/18 | 0/18 | 0/18 | 0/21 | 0/21 | 0/18 | 0/18 | 0/21 | 0/21 | 0/18 | 0/5 | 0/5 | 0/5 | 0/9 | 0/5 |
| 0x06012c8cf97bead5deae237070f9587f8e7a266d_uniqueFunction | yes | 0/204 | 0/302 | 0/204 | 0/204 | 2/204 | 0/302 | 0/302 | 0/204 | 0/204 | 0/302 | 0/302 | 0/204 | 0/59 | 0/59 | 0/59 | 0/182 | 0/59 |
| 0xb1690c08e213a35ed9bab7b318de14420fb57d8c_uniqueFunction | yes | 0/6 | 0/10 | 0/6 | 0/6 | 0/6 | 0/10 | 0/10 | 0/6 | 0/6 | 0/10 | 0/10 | 0/6 | 0/2 | 0/2 | 0/2 | 0/4 | 0/2 |
| 0x00000000219ab540356cbb839cbe05303d7705fa_uniqueFunction | yes | 0/9 | 0/17 | 0/9 | 0/9 | 0/9 | 0/17 | 0/17 | 0/9 | 0/9 | 0/17 | 0/17 | 0/9 | 0/1 | 0/1 | 0/1 | 0/8 | 0/1 |
| 0x323a76393544d5ecca80cd6ef2a560c6a395b7e3_uniqueFunction | yes | 0/21 | 0/31 | 0/21 | 0/21 | 0/21 | 0/31 | 0/31 | 0/21 | 0/21 | 0/31 | 0/31 | 0/21 | 0/6 | 0/6 | 0/6 | 0/12 | 0/6 |
| 0x9c8ff314c9bc7f6e59a9d9225fb22946427edc03_uniqueFunction | yes | 0/12 | 0/13 | 0/12 | 0/12 | 0/12 | 0/13 | 0/13 | 0/12 | 0/12 | 0/13 | 0/13 | 0/12 | 0/3 | 0/3 | 0/3 | 0/5 | 0/3 |
| 0x556b9306565093c855aea9ae92a594704c2cd59e_uniqueFunction | yes | 0/241 | 0/361 | 0/241 | 0/241 | 10/241 | 0/361 | 0/361 | 0/241 | 0/241 | 0/361 | 0/361 | 0/241 | 0/64 | 0/64 | 0/64 | 0/228 | 0/64 |
| 0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f_uniqueFunction | yes | 0/267 | 0/415 | 0/267 | 0/267 | 0/267 | 0/415 | 0/415 | 0/267 | 0/267 | 0/415 | 0/415 | 0/267 | 0/67 | 0/67 | 0/67 | 0/248 | 0/67 |
| 0x5e_cd49912 | yes | 0/4 | 0/5 | 0/4 | 0/4 | 0/4 | 0/5 | 0/5 | 0/4 | 0/4 | 0/5 | 0/5 | 0/4 | 0/2 | 0/2 | 0/2 | 0/3 | 0/2 |
| 0x5efda50f22d34f262c29268506c5fa42cb56a1ce_uniqueFunction | yes | 0/35 | 0/47 | 0/35 | 0/35 | 0/35 | 0/47 | 0/47 | 0/35 | 0/35 | 0/47 | 0/47 | 0/35 | 0/17 | 0/17 | 0/17 | 0/24 | 0/17 |
| 0xd90e2f925da726b50c4ed8d0fb90ad053324f31b_uniqueFunction | yes | 0/85 | 0/146 | 0/85 | 0/85 | 0/85 | 0/146 | 0/146 | 0/85 | 0/85 | 0/146 | 0/146 | 0/85 | 0/13 | 0/13 | 0/13 | 0/83 | 0/13 |
| 0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc_uniqueFunction | yes | 0/61 | 0/88 | 0/61 | 0/61 | 0/61 | 0/88 | 0/88 | 0/61 | 0/61 | 0/88 | 0/88 | 0/61 | 0/17 | 0/17 | 0/17 | 0/55 | 0/17 |
