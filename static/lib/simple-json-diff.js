// Simple JSON Diff Implementation
(function(global) {
    'use strict';

    function SimpleJsonDiff() {}

    SimpleJsonDiff.prototype.diff = function(left, right) {
        return this._diff(left, right, []);
    };

    SimpleJsonDiff.prototype._diff = function(left, right, path) {
        if (left === right) return null;
        
        if (left === null || right === null || 
            typeof left !== typeof right ||
            Array.isArray(left) !== Array.isArray(right)) {
            return {
                type: 'replace',
                path: path.slice(),
                left: left,
                right: right
            };
        }

        if (Array.isArray(left)) {
            return this._diffArray(left, right, path);
        }

        if (typeof left === 'object') {
            return this._diffObject(left, right, path);
        }

        return {
            type: 'replace',
            path: path.slice(),
            left: left,
            right: right
        };
    };

    SimpleJsonDiff.prototype._diffArray = function(left, right, path) {
        const changes = [];
        const maxLength = Math.max(left.length, right.length);

        for (let i = 0; i < maxLength; i++) {
            const leftValue = i < left.length ? left[i] : undefined;
            const rightValue = i < right.length ? right[i] : undefined;
            
            if (leftValue === undefined) {
                changes.push({
                    type: 'add',
                    path: path.concat([i]),
                    right: rightValue
                });
            } else if (rightValue === undefined) {
                changes.push({
                    type: 'remove',
                    path: path.concat([i]),
                    left: leftValue
                });
            } else {
                const childDiff = this._diff(leftValue, rightValue, path.concat([i]));
                if (childDiff) {
                    if (childDiff.type) {
                        changes.push(childDiff);
                    } else if (Array.isArray(childDiff)) {
                        changes.push(...childDiff);
                    }
                }
            }
        }

        return changes.length > 0 ? changes : null;
    };

    SimpleJsonDiff.prototype._diffObject = function(left, right, path) {
        const changes = [];
        const allKeys = new Set([...Object.keys(left), ...Object.keys(right)]);

        for (const key of allKeys) {
            const leftValue = left[key];
            const rightValue = right[key];

            if (!(key in left)) {
                changes.push({
                    type: 'add',
                    path: path.concat([key]),
                    right: rightValue
                });
            } else if (!(key in right)) {
                changes.push({
                    type: 'remove',
                    path: path.concat([key]),
                    left: leftValue
                });
            } else {
                const childDiff = this._diff(leftValue, rightValue, path.concat([key]));
                if (childDiff) {
                    if (childDiff.type) {
                        changes.push(childDiff);
                    } else if (Array.isArray(childDiff)) {
                        changes.push(...childDiff);
                    }
                }
            }
        }

        return changes.length > 0 ? changes : null;
    };

    // HTML Formatter
    function HtmlFormatter() {}

    HtmlFormatter.prototype.format = function(diff) {
        if (!diff) return '';
        
        if (!Array.isArray(diff)) {
            diff = [diff];
        }

        let html = '<div class="jsondiffpatch-visualdiff">';
        
        diff.forEach(change => {
            html += this._formatChange(change);
        });
        
        html += '</div>';
        return html;
    };

    HtmlFormatter.prototype._formatChange = function(change) {
        const pathStr = change.path.join('.');
        let html = '<div class="jsondiffpatch-change">';
        
        switch (change.type) {
            case 'add':
                html += `<div class="jsondiffpatch-added">+ ${pathStr}: ${this._formatValue(change.right)}</div>`;
                break;
            case 'remove':
                html += `<div class="jsondiffpatch-removed">- ${pathStr}: ${this._formatValue(change.left)}</div>`;
                break;
            case 'replace':
                html += `<div class="jsondiffpatch-changed">~ ${pathStr}:</div>`;
                html += `<div class="jsondiffpatch-removed">- ${this._formatValue(change.left)}</div>`;
                html += `<div class="jsondiffpatch-added">+ ${this._formatValue(change.right)}</div>`;
                break;
        }
        
        html += '</div>';
        return html;
    };

    HtmlFormatter.prototype._formatValue = function(value) {
        if (value === null) return 'null';
        if (value === undefined) return 'undefined';
        if (typeof value === 'string') return `"${value}"`;
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    // Global API
    global.simpleJsonDiff = {
        create: function() {
            return new SimpleJsonDiff();
        },
        formatters: {
            html: new HtmlFormatter()
        }
    };

    // Compatibility with jsondiffpatch API
    global.jsondiffpatch = global.simpleJsonDiff;

})(window);
