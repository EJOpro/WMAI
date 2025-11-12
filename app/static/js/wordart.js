let WordArt = (function () {
    const {isEmpty, isNotEmpty, descending, initShareMd, handleError} = Common;
    const {isAllowedMember} = Options;
    let chart, /*titleOption, */seriesOption, frequencies, dynaSwiper1 = '', dynaSwiper4 = '';
    /* const defaultRange = [60, 150];const limitRange = [60, 180];*/
    const STD_SERIES_OPTIONS = (() => {
        return {
            'sizeRange': [120, 280],
            'rotationRange': [0, 90],
            'rotationStep': 90,
            'rotateRatio': 1,
            'gridSize': 2,
            'fontDirection': {
                0: [[0, 0], 0, 1],
                1: [[90, 90], 90, 1],
                2: [[-45, -45], 0, 1],
                3: [[45, 45], 0, 1],
                4: [[-45, 45], 90, 1],
                5: [[0, 90], 90, 1],
                99: [[0, 90], 90, 1],
            },
            'defaultShape': 'square',
        };
    })();
    const MASK_IMAGE_PATH = 'images/wordart/mask/';
    const DEFAULT_RANK_SIZE = 100;

    const displayFocusedImg = (clickedEl) => {
        const displayedImg = document.querySelector('.focused-shape-box .focused-shape img');
        if (displayedImg) {
            if (clickedEl.querySelector('img') && clickedEl.querySelector('img').src) {
                if (displayedImg.classList.contains('ds-hid')) {
                    displayedImg.classList.remove('ds-hid');
                }
                displayedImg.src = clickedEl.querySelector('img').src;
            } else {
                if (!displayedImg.classList.contains('ds-hid')) {
                    displayedImg.classList.add('ds-hid');
                }
                // src="/kr/wordart/images/wordart/mask/mask_circle_preview.png"
                // alt="notice-focused-shape"
            }
        }
    };
    const getTitleOrDefault = (str) => {
        return ((value, defaultVal) => isEmpty(value) ? defaultVal : value)(str, '제목없는 티핑 워드클라우드');
    };
    const modifyBgData = (rgbData) => {
        function isLooksLikeWhite(r, g, b) {
            return r > 249 && g > 249 && b > 249;
        }

        function isHighTransparency(a) {
            return a < 52;
        }

        function isLooksLikeWhiteOrIsHighTransparency(r, g, b, a) {
            return isLooksLikeWhite(r, g, b) || isHighTransparency(a);
        }

        for (let i = 0, len = rgbData.length; i < len; i += 4) {
            let [r, g, b, a] = [
                rgbData[i], rgbData[i + 1], rgbData[i + 2], rgbData[i + 3]];
            if (isLooksLikeWhiteOrIsHighTransparency(r, g, b, a)) {
                rgbData[i + 3] = 0;
            }
        }
        return rgbData;
    };
    const setImageSource = (imageElement, source) => {
        if (source instanceof File) {
            const reader = new FileReader();
            reader.onload = e => imageElement.src = e.target.result;
            reader.onerror = e => {
                console.error('File reading error:', e);
                alert('파일을 읽어오는데 실패했습니다.');
            };
            reader.readAsDataURL(source);
        } else {
            imageElement.src = `${MASK_IMAGE_PATH}${source}`;
        }
        return imageElement;
    };

    /**
     * @param {HTMLImageElement} maskImage
     * @param {number} width
     * @param {number} height
     * @param {*} textForMask
     * @param {*} radioOption
     * @param {string} selectFont
     */
    const buildCustomTextMaskImage = (maskImage, width, height, textForMask, radioOption, selectFont) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        // const backgroundColor = buildBgColor();
        const fontSize = textForMask.length > 5 ? 150 : 200;
        canvas.id = 'cvs';
        canvas.width = width;
        canvas.height = height;
        canvas.style.display = 'contents';

        ctx.font = 'bold ' + fontSize + 'px ' + selectFont;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        // const textWidth = context.measureText(textForMask).width;

        const setBackground = (ctx, c, x, y, w, h) => {
            ctx.fillStyle = c;
            ctx.fillRect(x, y, w, h);
        };
        const setText = (ctx, c, t, x, y) => {
            ctx.fillStyle = c;
            ctx.fillText(t, x, y);
        };
        if (radioOption === 'OUT') {
            setBackground(ctx, 'black', 0, 0, canvas.width, canvas.height);
            setText(ctx, 'white', textForMask, canvas.width / 2, canvas.height / 2);
        } else {/*     if (radioOption.value === 'IN') { */
            setBackground(ctx, 'white', 0, 0, canvas.width, canvas.height);
            setText(ctx, 'black', textForMask, canvas.width / 2, canvas.height / 2);
        }
        maskImage.src = canvas.toDataURL('image/png');
    };

    /**
     * @param {HTMLImageElement | SVGImageElement | HTMLVideoElement | HTMLCanvasElement | ImageBitmap | OffscreenCanvas | VideoFrame} maskImage
     * @param {number} width
     * @param {number} height
     */
    const drawImageToCanvas = (maskImage, width, height) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.id = 'cvs';
        canvas.width = width;
        canvas.height = height;
        canvas.style.display = 'contents';
        ctx.drawImage(maskImage, 0, 0, canvas.width, canvas.height);
        return ctx;
    };

    const genWordCloud = () => {
        chart.setOption({/*title: titleOption, */series: [seriesOption]});
        chart.on('finished', async () => {
            document.querySelector('#main div').style.display = 'none';
            document.getElementById('wordCloudLoading').remove();
            await generateWordCloudImage()
                .then(s => initHrefWCImage(s))
                .then(s => s && addTotalCnt())
                .catch(e => {
                    alert('Err!r');
                    handleError(e)
                });
        });
    };
    /**
     * @param {HTMLImageElement} maskImage
     * @param {number} width
     * @param {number} height
     */
    const setupCanvasAndGenWordCloud = (maskImage, width, height) => {
        const ctx = drawImageToCanvas(maskImage, width, height);

        if (!maskImage.src.includes('_default_')) {
            const imageData = ctx.getImageData(0, 0, maskImage.width,
                maskImage.height);
            modifyBgData(imageData.data);
            ctx.putImageData(imageData, 0, 0);
        } else {
            seriesOption.maskImage = undefined;
            seriesOption.shape = STD_SERIES_OPTIONS.defaultShape;
        }
        genWordCloud();
    };

    /**
     * @param {number} width
     * @param {number} height
     * @param {string} selectFont
     * @returns {HTMLImageElement}
     */
    const buildMaskImage = (width, height, selectFont) => {
        const selectedMask = document.querySelector('.shape.focused');
        const maskImage = new Image();
        maskImage.onerror = () => console.error('Mask image load error');
        if (!!selectedMask) {
            if (selectedMask.tagName === 'BUTTON') {
                /* 프리셋 마스크 */
                const imagePath = selectedMask.querySelector('img').src.split(MASK_IMAGE_PATH)[1];
                setImageSource(maskImage, imagePath);
                maskImage.onload = () => setupCanvasAndGenWordCloud(maskImage, width, height);
            } else if (selectedMask.tagName === 'INPUT') {
                /* 업로드된 텍스트 마스크 */
                const textForMask = selectedMask.value;
                const radioOption = document.querySelector(".text_mask_options input[type='radio']:checked").value
                buildCustomTextMaskImage(maskImage, width, height, textForMask, radioOption, selectFont)
                maskImage.onload = () => setupCanvasAndGenWordCloud(maskImage, width, height);
            } else if (selectedMask.tagName === 'DIV') {
                /* 업로드된 커스텀 마스크 */
                const file = document.getElementById('maskCustom')?.files[0];
                if (file) {
                    setImageSource(maskImage, file);
                    maskImage.onload = () => setupCanvasAndGenWordCloud(maskImage, width, height);
                }
            }
        } else {
            /* 업로드된 커스텀 마스크 */
            const file = document.getElementById('maskCustom')?.files[0];
            if (file) {
                setImageSource(maskImage, file);
                maskImage.onload = () => setupCanvasAndGenWordCloud(maskImage, width, height);
            }
        }
        return maskImage;
    };

    async function analyze(a) {
        /*console.debug('analyze ==');*/
        const z = await fetch("https://www.tippingkorea.online/analyze", {
            method: "POST",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({a: a}),
        })
            .then(response => response.json())
            .catch(e => {
                throw new Error(`ERROR[001] - ${e.message}`);
            });
        // const result = z['data'];
        return z['data'];
    }

    /**
     * @param {string} textData
     * @param {string[]} strongKeywords
     * @param {string[]} notKeywords
     * @param {number} ranksSize
     * @param {number} selectWordNumber
     * @param {string} extractMethod
     *
     */
    const createWordFrequencyArray = async (textData, strongKeywords, notKeywords, ranksSize, selectWordNumber, extractMethod) => {
        /*console.debug('start == ');*/
        if (isEmpty(textData)) {
            document.getElementById('cttDataReset').click();
            alert('텍스트 내용이 비어있습니다. 단어목록을 입력해주세요.');
            throw new Error('text is empty');/*삭제금지*/
        } else {
            buildStatistics = (slicedWords) => {
                /*console.debug('buildStatistics ==');*/
                const buildDd = (content, className) => {
                        const ddEl = document.createElement('dd');
                        if (content) {
                            ddEl.textContent = content;
                        }
                        if (className) {
                            ddEl.className = className;
                        }
                        return ddEl;
                    },
                    buildDl = (children, className) => {
                        const dlEl = document.createElement('dl');
                        if (className) {
                            dlEl.className = className;
                        }
                        children.forEach(child => {
                            dlEl.appendChild(child);
                        })
                        return dlEl;
                    },
                    keywordStatistics = document.getElementById('keywordStatistics');
                keywordStatistics.innerHTML = '';
                slicedWords.forEach(([word, frequency]) => keywordStatistics.append(buildDl([buildDd(word), buildDd(frequency.toString())], 'd-flex')));

                /*z graph z*/
                Graph.genGraph(slicedWords);
            },
                containsKorean = (text) => /[가-힣]/.test(text),

                removeOuterWords = (text, exclusionWords, exclusionRegex, replaceWord) => text.replace(exclusionRegex, (replaceWord !== undefined && replaceWord !== null) ? replaceWord : ''),
                removeOuterWordsKor = (text, exclusionWords, replaceWord) => {
                    const regexPattern = '(' + exclusionWords.join(' | ') + ')';
                    const exclusionRegex = new RegExp(regexPattern, 'gi');
                    return removeOuterWords(text, exclusionWords, exclusionRegex, replaceWord);
                },
                removeOuterWordsEng = (text, exclusionWords, replaceWord) => {
                    const regexPattern = '\\b(' + exclusionWords.join('|') + ')\\b';
                    const exclusionRegex = new RegExp(regexPattern, 'g');
                    return removeOuterWords(text, exclusionWords, exclusionRegex, replaceWord);
                },
                removeKoreanLetters = (text) => text.replace(/[가-힣]/g, ''),
                removeEnglishLetters = (text) => text.replace(/[A-Za-z]/g, ''),
                removeOuterEnglishWords = (text) => {
                    const exclusionWords = [
                        'and', 'but', 'a', 'an', 'the', 'of', 'or', 'so', 'as', 'for', 'after',
                        'before', 'since', 'until', 'though', 'although', 'to', 'in', 'on',
                        'because', 'when', 'where', 'what', 'who', 'why', 'how', 'that',
                        'even', 'yet', 'while', 'by', 'without', 'is', 'was', 'were',
                        'have', 'had', 'are', 'i', 'we', 'you', 'she', 'he', 'him', 'her',
                        'this', 'has', 'been', 'does', 'not', 'no', 'Please', 'below',
                        'under', 'don’t', 'do', 'not', 'than'
                    ];
                    return removeOuterWordsEng(text, exclusionWords);
                },
                removeOuterKoreanWords = (text) => {
                    const exclusionWords = [
                        "그리고", "그런데", "그러나", "그래도", "그래서", "또는", "및", "즉",
                        "게다가", "따라서", "아니면", "왜냐하면", "단", "하지만", "오히려", "비록",
                        "한편", "예를들면", "만약", "여전히", "아직", "훨씬", "단연코", "매우",
                        "반면에", "더욱이", "특히", "그렇다면", "그렇지만"
                    ];
                    return removeOuterWordsKor(text, exclusionWords, ' ');
                },
                extractEnglishWords = (text) => {
                    const innerWordsText = removeOuterEnglishWords(text);
                    const engWordsText = removeKoreanLetters(innerWordsText);
                    const englishWords = engWordsText.match(/\b[A-Za-z']+\b/g);
                    return englishWords || [];
                },
                extractRemainWords = (text) => {
                    const tmpTextBf = removeEnglishLetters(text);
                    const tmpTextAft = removeKoreanLetters(tmpTextBf);
                    return tmpTextAft.split(/[\s|!?@#$%^&*():;+-=~{}<>_\[\]\\"',.\/`₩]+/g);/* 형태소 분석 들어가야 할 부분. */
                },
                modifiedText = /[A-Z]/.test(textData) ? textData.toLowerCase() : textData;

            let words;
            if (containsKorean(modifiedText)) {
                /*analyze korean*/
                const korWords = removeOuterKoreanWords(modifiedText);
                /*console.debug('korWords : ' + JSON.stringify({"value": korWords}));*/
                if (extractMethod === '1') {
                    words = modifiedText.split(/[\s|!?@#$%^&*():;+-=~{}<>_\[\]\\"',.\/`₩]+/g);
                } else if (extractMethod === '2' || extractMethod === '3') {
                    const result = await analyze(korWords);
                    words = result['word_list'];
                } else {
                    throw new Error('invalid extractMethod value.');
                }
                /*analyze english*/
                const engArr = extractEnglishWords(modifiedText);
                words.push(...engArr);
                /*analyze remained*/
                const tmpWords = extractRemainWords(modifiedText);
                words.push(...tmpWords);
            } else {
                /*analyze english*/
                words = extractEnglishWords(modifiedText);
                /*analyze remained*/
                const tmpWords = extractRemainWords(modifiedText);
                words.push(...tmpWords);
            }

            if (words.length < 1) {
                return [];
            } else {
                /*console.debug('createWordFrequencyArray ==');*/
                let wordFrequencies = {};

                if (extractMethod === '1' || extractMethod === '2') {
                    /* 빈도수 카운팅 */
                    words.forEach((word) => {
                        if (!notKeywords.includes(word) && isNotEmpty(word)) {
                            wordFrequencies[word] = (wordFrequencies[word] || 0) + 1;
                        }
                    });
                } else if (extractMethod === '3') {
                    const aggregateWordFrequency = (words, notKeywords) => {
                        const frequencyMap = new Map();
                        words.forEach(word => {
                            let found = false;
                            if (!notKeywords.includes(word) && isNotEmpty(word)) {
                                for (let key of frequencyMap.keys()) {
                                    if (word.includes(key) || key.includes(word)) {
                                        frequencyMap.set(key, frequencyMap.get(key) + 1);
                                        found = true;
                                        break;
                                    }
                                }
                                if (!found) {
                                    frequencyMap.set(word, 1);
                                }
                            }
                        });
                        return Object.fromEntries(frequencyMap);
                    };
                    wordFrequencies = aggregateWordFrequency(words, notKeywords);
                } else {
                    throw new Error('invalid extractMethod value.');
                }

                /* 빈도수 리스트 생성 */
                const sortedWords = Object.entries(wordFrequencies)
                    .filter(f => isNotEmpty(f[0]))
                    .sort((a, b) => b[1] - a[1]);

                const slicedWords = sortedWords.slice(0, ranksSize);

                buildStatistics(slicedWords);

                /* 워드클라우드 생성을 위한 전처리 */
                /* wordFrequencies[word] : 빈도수 */
                const wordListOrg = Object.keys(wordFrequencies)
                    .filter(isNotEmpty)
                    .map(word => ({name: word, value: wordFrequencies[word]}))
                    .sort(descending);

                /* 빈도수 엑셀 생성 전처리 */
                frequencies = createFreqExcelFile(wordListOrg);

                /* 빈도수 조정 */
                let maxFrequency = slicedWords[0][1];
                strongKeywords.forEach((word, index) => {
                    if (wordFrequencies.hasOwnProperty(word)) {
                        wordFrequencies[word] = maxFrequency + (30 / (index + 1));
                    }
                });

                const wordList = Object.keys(wordFrequencies)
                    .filter(isNotEmpty)
                    .map(word => ({name: word, value: wordFrequencies[word]}))
                    .sort(descending);

                const slicedWordList = wordList.slice(0, selectWordNumber),
                    config = document.querySelector("#font-configs > input[type='radio']:checked")?.value || '0',
                    isCus2ConfigEnabled = config === '2',
                    adjustFreq = (a, s) => {
                        const rs = [];
                        const names = a.map(r => r.name);
                        let c = 0;
                        for (let i = 0, len = names.length; i < len; i++) {
                            const word = names[i];
                            const rNames = rs.map(r => r.name);
                            if (s.includes(word) && !rNames[word]) {
                                console.debug(`sword[${i}: ${word}`);
                                // rs[word] = 80 - (10*c);
                                rs.push({'name': word, 'value': 80 - (10 * c)})
                                c++;
                            } else {
                                console.debug(`word: ${word}`);
                                // rs[word] = 1;
                                rs.push({'name': word, 'value': 1})
                            }
                        }
                        return rs;
                    };
                // TODO
                if (isCus2ConfigEnabled) {
                    function expandAndUnifyValues(d, m, s) {
                        const prv = d.map(t => ({'name': t.name, 'value': 1})),
                            ud = adjustFreq(prv, s);
                        const len = prv.length;
                        ww:while (ud.length < m) {
                            for (let i = 0; i < len; i++) {
                                let tp = prv[i];
                                if (tp) {
                                    tp['value'] = 1;
                                    ud.push({...tp});
                                }
                                if (ud.length >= m) {
                                    break ww;
                                }
                            }
                        }
                        return ud;
                    }

                    return expandAndUnifyValues(slicedWordList, selectWordNumber, strongKeywords);
                } else {
                    return slicedWordList;
                }
            }
        }
    };

    /**
     *
     * @param {{name: *, value: *}[]} wordFrequencies
     * @returns {FormData}
     */
    const createFreqExcelFile = (wordFrequencies) => {
        const DEF_EXT = "xlsx", HEADER_CELLS = ['단어', '빈도'], DEF_SHEET_NM = '단어빈도분석',
            MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        const convertStringToArrayBuffer = (s) => {
            const len = s.length, buf = new ArrayBuffer(len), view = new Uint8Array(buf);
            for (let i = 0; i < len; i++) view[i] = s.charCodeAt(i) & 0xFF;
            return buf;
        };

        const workbook = XLSX.utils.book_new();
        const worksheetData = [HEADER_CELLS];
        wordFrequencies.forEach(item => worksheetData.push([item.name, item.value]));
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);
        XLSX.utils.book_append_sheet(workbook, worksheet, DEF_SHEET_NM);

        // 엑셀 파일 생성 (브라우저에서 다운로드)// XLSX.writeFile(workbook, 'WordsFrequency.xlsx');
        const binaryString = XLSX.write(workbook, {bookType: DEF_EXT, type: 'binary'});
        const blob = new Blob([convertStringToArrayBuffer(binaryString)], {type: MIME_TYPE});
        const DEF_FILE_NM = createFileName();

        // down-freq-excel TEST
        const url = URL.createObjectURL(blob);
        const anchor = document.querySelector(".down-freq-excel");
        anchor.href = url;
        anchor.download = `${DEF_FILE_NM}.${DEF_EXT}`;
        // down-freq-excel TEST @X@

        return createSingleFormData("excel", blob, 'freq_rank.xlsx');
    };

    /**
     *
     * @returns {`티핑-단어빈도분석_${number}${string}${string}`}
     */
    const createFileName = () => {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        const day = now.getDate().toString().padStart(2, '0');
        return `티핑-단어빈도분석_${year}${month}${day}`;
    };

    /**
     *
     * @param text
     * @returns {*}
     */
    const escapeHTML = (text) => {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     *
     * @param attrNm
     * @param value
     * @param fName
     * @returns {FormData}
     */
    const createSingleFormData = (attrNm, value, fName) => {
        if (!attrNm || typeof attrNm !== 'string') {
            throw new Error('Invalid or missing "name" parameter.');
        }
        if (value === 'undefined') {
            throw new Error('Missing "value" parameter.');
        }
        const formData = new FormData();
        if (value instanceof Blob) {
            formData.append(attrNm, value, fName || 'blob');
        } else {
            formData.append(attrNm, value);
        }
        /*console.debug(`attrNm: ${attrNm} /| ${value} |\\ ${fName}`)*/
        return formData;
    };

    /**
     * @param {Request | string | URL} dataUrl
     * @returns {Promise<Blob>}
     */
    const getImageToBlob = async (dataUrl) => await fetch(dataUrl).then(response => response.blob());
    const getTextToBlob = (text) => {
        return new Blob([escapeHTML(text)], {type: "text/plain"});
    };
    const getContentFormData = (fElNm, tElNm) => {
        try {
            const fData = document.getElementById(fElNm);
            if (fData.files && isNotEmpty(fData.files[0]) && isNotEmpty(fData.files[0]['name'])) {
                return createSingleFormData("file", fData.files[0], fData.files[0].name);
            } else {
                const tData = document.getElementById(tElNm).value || 'DATA_IS_EMPTY';
                if (typeof tData === 'string') {
                    return createSingleFormData("file", getTextToBlob(tData), "wc-ctt.txt");
                } else {
                    return '';
                }
            }
        } catch (e) {
            /*console.error('ERR: ', e);*/
            throw new Error(`업로드에 실패했습니다. cause: ${e.message}`);
        }
    };

    /**
     * @param {FormData} fData
     * @returns {Promise<any|null>}
     */
    const uploadFile = async (fData) => {
        const rst = await fetch("/kr/wordart/gallery/arts_upload.php", {
            method: "POST",
            body: fData,
        })
            .then(response => response.json())
            .catch(e => {
                handleError(e);
                throw new Error(`${e.message}`);
            });
        /*console.debug(rst);*/
        if (!rst) {
            /*console.error('rst: ' + rst);*/
            return null;
        } else if (rst['m']) {
            if (rst['m'].indexOf("세션") !== -1) {
                alert(rst.m);
                location.href = "/kr/member/private_login.php?login_go=/kr/wordart/index.php";
            } else {
                console.error(rst['m']);
                alert(rst.m);
                return null;
            }
        } else {
            return rst;
        }
    };
    const uploadWCImage = async () => {
        const imgEl = document.getElementById("wordCloudImage");
        const imageUrl = imgEl.getAttribute("src");
        if (imageUrl.indexOf('default_result') !== -1) {
            alert('워드클라우드 생성 후 저장 버튼을 눌러주세요.');
            return '';
        }
        const blob = await getImageToBlob(imageUrl);
        const fData = createSingleFormData("image", blob, 'wc-img.png');
        return await uploadFile(fData);
    };
    const uploadWCContent = async () => {
        const fData = getContentFormData("cttFileUpload", "textData");
        if (fData !== '') {
            return await uploadFile(fData);
        }
    };
    const uploadWCFreqExcel = async () => {
        return await uploadFile(frequencies);
    };
    const saveWordArtToGallery = async e => {
        e.stopPropagation();
        try {
            const imgEl = document.getElementById("wordCloudImage");
            const imageUrl = imgEl.getAttribute("src");
            if (imageUrl.indexOf('default_result') !== -1) {
                alert('워드클라우드 생성 후 저장 버튼을 눌러주세요.');
                return -1;
            } else {
                const iid = await uploadWCImage(),
                    cid = await uploadWCContent(),
                    xid = await uploadWCFreqExcel();
                if (!iid || !cid || !xid) {
                    return -1;
                }
                const t = getTitleOrDefault(document.getElementById('title').value);
                const rst = await fetch("/kr/wordart/gallery/arts_c_gallery.php", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        g: {t: t}, i: iid, c: cid, x: xid
                    }),
                })
                    // .then(response => response.text())
                    .then(response => response.json())
                    .then(rs => rs.data)
                    .catch(e => {
                        /*console.error('ERR: ', e);*/
                        alert('저장에 실패했습니다.');
                        throw new Error(`저장에 실패했습니다. cause: ${e.message}`);
                    });
                if (!!rst && rst['m']) {
                    if (rst['m'].indexOf("세션") !== -1) {
                        alert(rst.m);
                        location.href = "/kr/member/private_login.php?login_go=/kr/wordart/index.php";
                    } else {
                        console.error(rst['m']);
                        alert(rst.m);
                    }
                } else if (rst > 0) {
                    alert('저장되었습니다.');
                    return 0;
                }
                return -1;
            }
        } catch (e) {
            /*console.error('ERR: ', e);*/
            alert('저장에 실패했습니다.');
            throw new Error(`저장에 실패했습니다. cause: ${e.message}`);
        }
    };

    /**
     *
     * @param {Event} e
     */
    const generateWordCloud = async e => {
        e.stopPropagation();
        (() => {
            const resultBox = document.querySelector('#resultBox');
            const main = resultBox.querySelector('#main');
            if (main) {
                main.removeAttribute('_echarts_instance_');
                main.removeAttribute('style');
                main.style.display = 'none';
            }
            const mainDiv = main.querySelector('div.result');
            if (mainDiv) {
                mainDiv.removeAttribute('style');
                mainDiv.innerHTML = '';
                mainDiv.style.display = 'none';
            }
            const wcImage = resultBox.querySelector('#wordCloudImage');
            if (wcImage) {
                wcImage.src = '/kr/wordart/images/wordart/default_result.png';
                wcImage.style.display = 'none';
            }
        })();

        /**
         *
         * @returns {(number[]|number)[]}
         */
        const getFontDirection = () => STD_SERIES_OPTIONS.fontDirection[Number(document.getElementById('textDirection').value || 99)];

        /**
         *
         * @returns {[number,number]}
         */
        const getFontSize = () => {
            const config = (() => document.querySelector("#font-configs > input[type='radio']:checked")?.value || '0')(),
                getNumber = val => Number(val.trim());
            if ('1' === config) {
                return [getNumber(document.getElementById('minFontSize').value),
                    getNumber(document.getElementById('maxFontSize').value)];
            } else if ('2' === config) {
                const cn = getNumber(document.getElementById('constantFontSize').value);
                const strongKeywords = getOrderedKeywords('#strongKeywords input[type="text"]');
                if (strongKeywords.length > 0) {
                    return [cn, cn + 150];/*@X*/
                } else {
                    return [cn, cn];
                }
            } else {
                return [Number(STD_SERIES_OPTIONS.sizeRange[0]), Number(STD_SERIES_OPTIONS.sizeRange[1])];
            }
        };

        /**
         *
         * @returns {*|*[]}
         */
        const getScreenSize = () => {
            const screenSizeInput = document.querySelector('#screenSize').value.trim();
            if (screenSizeInput) {
                return screenSizeInput.split('*').map(size => size.trim());
            }
            return [
                document.querySelector('#screenSizeWidthFix').value.trim(),
                document.querySelector('#screenSizeHeightFix').value.trim()];
        };

        /**
         *
         * @param {string} selector
         * @returns {*[]}
         */
        const getOrderedKeywords = (selector) => {
            return Array.from(document.querySelectorAll(selector)).map(input => input.value).filter(isNotEmpty).map(v => v.trim()).reduce((unique, item) => unique.includes(item) ?
                unique :
                [...unique, item], []);
        };

        async function getData() {
            document.getElementById('resultBox').classList.remove('hid');
            document.getElementById('resultViewBtn').classList.add('on');
            document.getElementById('resultViewBtn').textContent = '결과 닫기';
            document.getElementById('resultViewBtn').scrollIntoView();

            const textData = document.getElementById('textData').value;
            const selectWordNumber = document.querySelector('#wordNumber').value;
            const strongKeywords = getOrderedKeywords('#strongKeywords input[type="text"]');
            const stopKeywords = getOrderedKeywords('#notKeywords input[type="text"]');
            let extractMethod = document.querySelector('#extractMethods input[checked="checked"]').value;
            return await createWordFrequencyArray(textData, strongKeywords, stopKeywords, DEFAULT_RANK_SIZE, selectWordNumber, extractMethod)
        }

        const getFontColors = (isStdConfig) => {
            if (isStdConfig) {
                const getColorValue = () => document.getElementById('colorSelect').value;
                return () => `rgb(${evaluate_cmap(Math.random(), getColorValue(), false).join(', ')})`;
            } else {
                const getRandomElement = (arr) => arr[Math.floor(Math.random() * arr.length)];
                const customFtColors = Array.from(document.querySelectorAll('#customFontColors .color-picker')).map(m => m.value);
                return () => getRandomElement(customFtColors);
            }
        };

        function createWordCloud(freqArray) {
            const config = (() => document.querySelector("#font-configs > input[type='radio']:checked")?.value || '0')(),
                isStdConfigEnabled = '0' === config,
                getFontColorFnc = getFontColors(isStdConfigEnabled),
                presetFontFamily = document.getElementById('fontSelect').value,
                [selectWidth, selectHeight] = getScreenSize(),
                width = selectWidth, height = selectHeight,
                [selectFtMin, selectFtMax] = getFontSize(),
                textDirection = getFontDirection(),
                textGap = Number(document.getElementById('textGap').value),
                loadingEl = document.createElement('div');

            loadingEl.id = 'wordCloudLoading';
            loadingEl.innerHTML = '<div class="spinner"></div>';
            document.querySelector('#wordCloudImage').after(loadingEl);
            chart = echarts.init(document.getElementById('main'), null, {width, height});

            seriesOption = {
                type: 'wordCloud',
                width: width,
                height: height,
                sizeRange: isStdConfigEnabled ? STD_SERIES_OPTIONS.sizeRange : [selectFtMin, selectFtMax],
                rotationRange: isStdConfigEnabled ? STD_SERIES_OPTIONS.rotationRange : textDirection[0],
                rotationStep: isStdConfigEnabled ? STD_SERIES_OPTIONS.rotationStep : textDirection[1],
                rotateRatio: isStdConfigEnabled ? STD_SERIES_OPTIONS.rotateRatio : textDirection[2],
                gridSize: isStdConfigEnabled ? STD_SERIES_OPTIONS.gridSize : textGap,
                maskImage: buildMaskImage(width, height, presetFontFamily),
                drawOutOfBound: false,
                keepAspect: true,
                shrinkToFit: true,
                textStyle: {
                    fontFamily: presetFontFamily,
                    fontWeight: 'bold',
                    color: getFontColorFnc,
                },
                data: freqArray,
            };
            /*console.debug('@@@@@@-SHP-@@@@@@@');
            console.debug(seriesOption);
            console.debug('@@@@@@-SHP-@@@@@@@');*/
        }

        getData().then(arr => createWordCloud(arr)).catch(e => handleError(e));
    };
    const buildBgColor = () => {
        const selectBgColor = document.querySelector('#bgColors .focused');
        const selectBgTransparent = document.querySelector('#bgTransparent.focused');
        const selectBgPicker = document.querySelector('#bgPickerInput');
        return selectBgColor ? selectBgColor.style.backgroundColor :
            selectBgTransparent ? selectBgTransparent.style.backgroundColor :
                selectBgPicker.value;
    };

    /**
     *
     */
    const generateWordCloudImage = async () => {
        const img = document.getElementById('wordCloudImage');
        img.src = chart.getDataURL({
            type: 'png',
            pixelRatio: 7,
            backgroundColor: buildBgColor(),
        });
        img.alt = 'wordCloud image';
        img.style.width = document.querySelector('#main canvas').style.width;
        img.style.height = 'auto';
        img.style.display = 'block';
        return img.src;
    };
    const initHrefWCImage = async (src) => {
        const link = document.querySelector('#saveAsImage');
        if (src.indexOf('image/png') !== -1) {
            link.href = src.replace('image/png', 'image/octet-stream');
        }
        return Promise.resolve(true);
    };
    const selectCustomMask = e => {
        // e.stopPropagation();
        const selectedShape = document.querySelector('#shapes .focused');
        selectedShape?.classList.remove('focused');

        const targetMask = e.currentTarget;
        const img = document.getElementById('wordCloudImage');
        const maskCustomPreview = document.getElementById('maskCustomPreview');
        const previewBox = maskCustomPreview.querySelector('.preview-box');

        targetMask.classList.add('focused');
        if (targetMask.files.length > 0) {
            const file = targetMask.files[0];
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();

                reader.onload = ({target}) => {
                    previewBox.innerHTML = '';
                    const imgEl = document.createElement('img');
                    imgEl.src = target.result;
                    imgEl.alt = '업로드한 마스크 이미지 미리보기';
                    previewBox.append(imgEl);
                    maskCustomPreview.classList.add('focused');
                    document.getElementById('deleteMaskImg').classList.add('show');
                    displayFocusedImg(previewBox);
                    previewBox.querySelector('img')?.addEventListener('click', e => {
                        document.querySelector("#shapes .shape.focused").classList.remove('focused');
                        maskCustomPreview.classList.add('focused');
                    });
                };

                reader.onerror = (error) => {
                    console.error('File reading error:', error);
                    alert('파일을 읽어오는데 실패했습니다.');
                };
                reader.readAsDataURL(file);
            } else {
                alert('지원하는 이미지 파일 형식은 .jpg, .png 등입니다. 해당 형식의 파일을 선택해주세요.');
                resetImagePreview(previewBox, img);
                previewBox.innerHTML = '';
                img.alt = '이미지 마스크가 선택되지 않았습니다.';
            }
        } else {
            alert('파일을 선택해주세요.');
            resetImagePreview(previewBox, img);
        }
    };

    /**
     *
     * @param {Event} e
     */
    const selectRadioOption = e => {
        e.stopPropagation();
        const el = e.currentTarget;
        const pel = el.parentNode;
        pel.querySelector("input[type='radio']:checked").removeAttribute('checked');
        el.setAttribute('checked', 'checked');
    };
    const resetImagePreview = (maskCustomPreviewBox, imgEl) => {
        maskCustomPreviewBox.innerHTML = '';
        imgEl.src = '/kr/wordart/images/wordart/default_result.png';
        imgEl.alt = '이미지 마스크가 선택되지 않았습니다.';
    };
    const selectFontFamily = e => {
        e.stopPropagation();
        e.target.style.fontFamily = document.querySelector('#fontSelect').value;
    };
    const selectFontColorMap = e => {
        e.stopPropagation();
        document.querySelectorAll("#customFontColors .color-picker.focused").forEach((el) => {
            el.classList.remove('focused');
        });
    };
    const selectCustomFtColor = e => {
        document.querySelectorAll("#colorSelect .focused")
            .forEach(el => el.classList.remove('focused'));
        e.currentTarget.parentNode.classList.add('focused');
    };
    const selectBgTransparent = e => {
        e.stopPropagation();
        document.querySelector('#bgColors .focused')?.classList.remove('focused');
        document.querySelector('#bgPicker.focused')?.classList.remove('focused');
        e.target.classList.add('focused');
    };
    const focusBgPicker = e => {
        e.stopPropagation();
        document.querySelector('#bgColors .focused')?.classList.remove('focused');
        document.querySelector('#bgTransparent.focused')?.classList.remove('focused');
        document.getElementById('bgPicker').classList.add('focused');
    };
    const selectBgColor = e => {
        e.stopPropagation();

        const bgTransparent = document.querySelector('#bgTransparent.focused');
        const bgPicker = document.querySelector('#bgPicker.focused');

        if (bgTransparent) bgTransparent.classList.remove('focused');
        if (bgPicker) bgPicker.classList.remove('focused');

        const clickedElement = e.target;

        if (clickedElement.classList.contains('color')) {
            const colorButtons = document.querySelectorAll('.color');
            colorButtons.forEach(button => {
                button.classList.remove('focused');
            });
            clickedElement.classList.add('focused');
        }
    };

    const selectMask = e => {
        e.stopPropagation();
        const shapes = document.getElementById('shapes');
        if (isAllowedMember()) {
            const clickedEl = e.target;
            if (clickedEl.classList.contains('shape')) {
                shapes.querySelectorAll('.shape.focused')?.forEach(btn => btn.classList.remove('focused'));
                clickedEl.classList.add('focused');
                displayFocusedImg(clickedEl);
            }
        } else {
            alert(shapes.dataset.loginMsg);
            location.href = `/kr/member/private_login.php?login_go=${shapes.dataset.pageUrl}`
        }
    };

    const selectScreenSize = e => {
        e.stopPropagation();
        e.preventDefault();
        const screenSizeWidthFix = document.getElementById('screenSizeWidthFix');
        const screenSizeHeightFix = document.getElementById('screenSizeHeightFix');

        if (e.target.value === '') {
            screenSizeWidthFix.disabled = false;
            screenSizeHeightFix.disabled = false;
        } else {
            screenSizeWidthFix.disabled = true;
            screenSizeHeightFix.disabled = true;
        }
    };
    /*#wcSpotBn*/
    const initSwiper = (elIdSelector) => {
        return new Swiper(elIdSelector + ' ' + '.recom-img-container', {
            slidesPerView: '1',
            paginationClickable: true,
            pagination: elIdSelector + ' ' + '.recom-img-banner-paging',
            nextButton: elIdSelector + ' ' + '.recom-img-banner-next',
            prevButton: elIdSelector + ' ' + '.recom-img-banner-prev',
            spaceBetween: 0,
            freeMode: false,
            loop: true,
            speed: 500,
            breakpoints: {
                851: {
                    centeredSlides: true,
                    spaceBetween: 10,
                }
            }
        });
        // return swiVar.nm;
    }
    const initTab = async (tabName) => {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        tabButtons?.forEach(button => button.classList.remove('active'));
        tabContents?.forEach(content => content.classList.add('ds-hid'));
        window.sessionStorage.setItem('tab', tabName);

        const selectedButton = document.querySelector(`#${tabName}-button`);
        const selectedContent = document.querySelector(`#${tabName}`);
        selectedButton.classList.add('active');
        selectedContent.classList.remove('ds-hid');

        if (tabName === 'tab2') {
            if (isAllowedMember()) {
                document.getElementById('gallery-grid-box').innerHTML = '';
                document.getElementById("galleryPagingBar").innerHTML = '';
                await Gallery.searchGallery(1);
            } else {
                alert(document.getElementById('shapes').dataset['loginMsg']);
            }
        } else if(tabName === 'tab1') {
            if(!dynaSwiper1) {
                dynaSwiper1 = initSwiper('#wcSpotBn');
                if(!!document.querySelector('#resultBox')) {
                    document.querySelector('#resultBox').classList.add('hid');
                }
            }
        } else if(tabName === 'tab4') {
            if(!dynaSwiper4) {
                dynaSwiper4 = initSwiper('#wcnkSpotBn');
            }
        }
    };
    const initializeTabs = () => {
        if (isNotEmpty(window.sessionStorage.getItem('tab'))) {
            initTab(window.sessionStorage.getItem('tab'));
        } else {
            initTab('tab1');
        }
    };
    const openTab = async (tabName) => {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        tabButtons?.forEach(button => button.classList.remove('active'));
        tabContents?.forEach(content => content.classList.add('ds-hid'));

        const selectedButton = document.querySelector(`#${tabName}-button`);
        const selectedContent = document.querySelector(`#${tabName}`);
        selectedButton.classList.add('active');
        selectedContent.classList.remove('ds-hid');

        if (tabName === 'tab2') {
            document.getElementById('gallery-grid-box').innerHTML = '';
            document.getElementById("galleryPagingBar").innerHTML = '';
            if (isAllowedMember()) {
                await Gallery.searchGallery(1);
            } else {
                alert(document.getElementById('shapes').dataset['loginMsg']);
                location.href = "/kr/member/private_login.php?login_go=https://www.tippingkorea.co.kr/kr/wordart/index.php";
            }
        } else if (tabName === 'tab1' && 'tab1' !== window.sessionStorage.getItem('tab')) {
            if (Main.isInited === 1) {
                /*console.debug('reInitShapes == ');*/
                Options.initShapes();
                Main.isInited++;
            }
            if(!dynaSwiper1) {
                dynaSwiper1 = initSwiper('#wcSpotBn');
            }
        } else if (tabName === 'tab4' && 'tab4' !== window.sessionStorage.getItem('tab')) {
            if(!dynaSwiper4) {
                dynaSwiper4 = initSwiper('#wcnkSpotBn');
            }
        }
        window.sessionStorage.setItem('tab', tabName);
    };

    const resultView = () => {
        const resultViewBtn = document.querySelector('#resultViewBtn');
        const resultBox = document.querySelector('#resultBox');
        if (resultBox.classList.contains('hid')) {
            resultViewBtn.classList.add('on');
            resultBox.classList.remove('hid');
            resultViewBtn.innerText = '결과 닫기';
        } else {
            resultViewBtn.classList.remove('on');
            resultBox.classList.add('hid');
            resultViewBtn.innerText = '결과 보기';
        }
    };

    const deleteMaskCustom = e => {
        let oldInput = document.getElementById('maskCustom');
        let newInput = document.createElement('input');
        newInput.type = 'file';
        newInput.id = oldInput.id;
        newInput.name = oldInput.name;
        newInput.className = oldInput.className;
        newInput.accept = oldInput.accept;
        newInput.style = oldInput.style;
        newInput.addEventListener('change', selectCustomMask);
        oldInput.parentNode.replaceChild(newInput, oldInput);

        const previewBox = document.querySelector('#maskCustomPreview .preview-box');
        if (previewBox) {
            previewBox.innerHTML = '';
        }
        document.querySelectorAll('#shapes .shape.focused')?.forEach(btn => btn.classList.remove('focused'));
        const clickedEl = document.querySelectorAll('#shapeBasic .shape')[0];
        clickedEl.classList.add('focused');
        displayFocusedImg(clickedEl);

        //@@@
        document.getElementById('deleteMaskImg').classList.remove('show');
    };
    const openShareMainModal = e => {
        /* Necessary things already loaded elements => .share-to-friends button & .share-modal */
        e.stopPropagation();
        const imgUrl = document.getElementById('wordCloudImage').src;
        const webUrl = "/kr/wordart/index.php";
        initShareMd('.share-modal-pc', 'share-modal-main', 'upper-pc', '', imgUrl, webUrl, '', '', '');
        initShareMd('.share-modal-mb', 'share-modal-main', 'upper-mb', '', imgUrl, webUrl, '', '', '');
    };
    const selectMethodOption = e => {
        e.stopPropagation();
        document.querySelector('#extractMethods input[checked="checked"]')?.removeAttribute('checked');
        // document.querySelectorAll('#extractMethods input[checked="checked"]')
        //     .forEach(el => el.removeAttribute('checked'));
        // e.currentTarget.setAttribute('checked', 'checked');
        e.currentTarget.setAttribute('checked', 'checked');
    };

    async function plus1TC(id) {
        return await fetch("/kr/wordart/statistics/arts_c_statistics.php", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({id: id}),
        }).then(res => {
            if (res.ok) {
                return Promise.resolve(true);
            } else {
                throw new Error(`E9192_${res.status} : ${res.text() || '-'}`);
            }
        }).catch(e => {
            throw new Error(`[${e.status}] ${e.message}`);
        });
    }

    async function findTotalCnt(id) {
        return await fetch("/kr/wordart/statistics/arts_r_statistics.php", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({id: id}),
        }).then(res => {
            if (res.ok) {
                return Promise.resolve(res.json());
            } else {
                throw new Error(`E9193_${res.status} : ${res.text() || '-'}`);
            }
        }).catch(e => {
            throw new Error(`[${e.status}] ${e.message}`);
        });
    }

    function displayWcCnt(cnt) {
        try {
            const cntEls = document.querySelectorAll('.wordart .total .wcCnt'),
                formattedCnt = cnt.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            cntEls.forEach(el => el.textContent = formattedCnt);
        } catch (e) {
            handleError(e);
            new Error(`[${e.status}] ${e.message}`);
        }
        return cnt;
    }

    async function bringTotalCnt() {
        return await findTotalCnt('xy11042fafkF1kkd@b2m3amek@1la').then(r => r['data'] || 0);
    }

    async function setWcCnt() {
        bringTotalCnt()
            .then(c => displayWcCnt(c))
            .catch(e => {
                alert('E!!o!');
                handleError(e);
                return false;
            });
        return true;
    }

    async function addTotalCnt() {
        return await plus1TC('b2r12rgEk2krm-3b3mbsS2Xf1x')
            .then(s => s && setWcCnt())
            .then(s => s ? Promise.resolve(true) : Promise.reject(false))
            .catch(e => {
                console.error(`${e && e.message ? e.message : 'Error - plus1TC'}`);
                throw new Error(`집계처리에 실패했습니다. cause: ${e.message}`);
            });
    }

    return {
        selectFontColorMap: selectFontColorMap,
        selectFontFamily: selectFontFamily,
        selectCustomFtColor: selectCustomFtColor,
        selectBgTransparent: selectBgTransparent,
        focusBgPicker: focusBgPicker,
        selectBgColors: selectBgColor,
        selectMask: selectMask,
        selectCustomMask: selectCustomMask,
        selectRadioOption: selectRadioOption,
        selectScreenSize: selectScreenSize,
        saveWordArtToGallery: saveWordArtToGallery,
        genWordArt: generateWordCloud,
        initializeTabs: initializeTabs,
        openTab: openTab,
        resultView: resultView,
        deleteMaskCustom: deleteMaskCustom,
        getImageToBlob: getImageToBlob,
        openShareMainModal: openShareMainModal,
        selectMethodOption: selectMethodOption,
        setWcCnt: setWcCnt,
    };
})();